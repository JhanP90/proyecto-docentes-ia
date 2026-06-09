# backend/api/v1/endpoints/hojas_vida.py
"""
Router de Hojas de Vida (PDFs).

Endpoints:
  POST   /api/v1/hojas-vida/upload          → Subir PDF e iniciar extracción con IA
  GET    /api/v1/hojas-vida/mi-hoja         → Obtener hoja de vida del aspirante autenticado
  GET    /api/v1/hojas-vida/{id}/datos-ia   → Ver datos extraídos por Gemini
  POST   /api/v1/hojas-vida/{id}/validar    → Aspirante confirma/corrige los datos de la IA
  DELETE /api/v1/hojas-vida/{id}            → Eliminar hoja de vida (permite subir de nuevo)

Diseño del flujo de upload:
  1. Recibe el PDF → valida tipo y tamaño.
  2. Guarda el archivo en disco con nombre único (UUID).
  3. Crea registro `HojaDeVida` en BD con estado=PENDIENTE.
  4. Retorna 202 Accepted con la hoja_de_vida_id.
  5. Un BackgroundTask ejecuta la extracción con IA en segundo plano.
  6. El frontend puede hacer polling a /mi-hoja para ver el estado.
"""
import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    BackgroundTasks, status
)
from sqlalchemy.orm import Session

from database import get_db
from models import HojaDeVida, DatosExtraidosIA, Aspirante, EstadoProcesamiento
from schemas import (
    HojaDeVidaRead,
    DatosExtraidosIARead,
    DatosExtraidosValidar,
    DatosExtraidosGemini,
)
from core.config import settings
from core.dependencies import require_aspirante
from services.pdf_service import extraer_texto_pdf
from services.ia_service import extraer_datos_cv

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Utilidades internas ──────────────────────────────────────────

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
}

def _validar_archivo(file: UploadFile) -> None:
    """Valida que el archivo sea PDF y no exceda el tamaño máximo."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Solo se aceptan archivos PDF.",
        )


def _guardar_archivo(contenido: bytes, aspirante_id: str, nombre_original: str) -> tuple[str, str]:
    """
    Guarda el archivo en disco dentro de una carpeta por aspirante.

    Returns:
        (ruta_relativa, nombre_guardado)
    """
    carpeta = Path(settings.UPLOAD_DIR) / str(aspirante_id)
    carpeta.mkdir(parents=True, exist_ok=True)

    # Nombre único: uuid_nombreoriginal.pdf (preserva el nombre para trazabilidad)
    nombre_seguro = Path(nombre_original).stem[:50]  # max 50 chars del nombre original
    nombre_guardado = f"{uuid.uuid4().hex}_{nombre_seguro}.pdf"
    ruta_completa = carpeta / nombre_guardado

    with open(ruta_completa, "wb") as f:
        f.write(contenido)

    # Retornamos la ruta relativa al directorio de trabajo
    ruta_relativa = str(ruta_completa)
    return ruta_relativa, nombre_guardado


def _procesar_con_ia(hoja_vida_id: str, ruta_archivo: str) -> None:
    """
    Tarea de fondo: extrae texto del PDF → llama a Gemini → guarda resultado.
    Se ejecuta en un BackgroundTask de FastAPI (hilo separado, misma BD).

    Si ocurre cualquier error, actualiza el estado a ERROR con el mensaje.
    """
    from database import SessionLocal
    db = SessionLocal()
    
    logger.info("Iniciando extraccion IA para hoja_vida_id=%s", hoja_vida_id)

    # Obtener la hoja de vida fresca (la sesión de BD es nueva en el background)
    hoja = db.query(HojaDeVida).filter(HojaDeVida.id == (uuid.UUID(hoja_vida_id) if isinstance(hoja_vida_id, str) else hoja_vida_id)).first()
    if not hoja:
        logger.error("HojaDeVida %s no encontrada en background task", hoja_vida_id)
        db.close()
        return

    try:
        # ── Estado: PROCESANDO ──────────────────────────────────
        hoja.estado_procesamiento = EstadoProcesamiento.PROCESANDO
        db.commit()

        # ── Paso 1: Extraer texto del PDF ───────────────────────
        resultado_pdf = extraer_texto_pdf(ruta_archivo)

        if resultado_pdf.advertencias:
            logger.warning(
                "Advertencias PDF [%s]: %s",
                hoja_vida_id, " | ".join(resultado_pdf.advertencias)
            )

        # ── Paso 2: Llamar a Gemini ─────────────────────────────
        # Si GEMINI_API_KEY no está configurada, usamos el mock para no bloquear el desarrollo
        if settings.GEMINI_API_KEY:
            datos_ia = extraer_datos_cv(resultado_pdf.texto)
        else:
            logger.warning(
                "GEMINI_API_KEY no configurada — usando datos mock para hoja_vida_id=%s",
                hoja_vida_id
            )
            from services.ia_service import extraer_datos_cv_mock
            datos_ia = extraer_datos_cv_mock()

        # ── Paso 3: Guardar en BD ───────────────────────────────
        # Verificar si ya existe un registro (ej: reintento)
        datos_existentes = db.query(DatosExtraidosIA).filter(
            DatosExtraidosIA.hoja_vida_id == hoja_vida_id
        ).first()

        if datos_existentes:
            # Actualizar el registro existente
            datos_existentes.json_estructurado = datos_ia.model_dump()
            datos_existentes.json_validado = None
            datos_existentes.validado_por_aspirante = False
            datos_existentes.fecha_validacion = None
        else:
            nuevo_dato = DatosExtraidosIA(
                hoja_vida_id=hoja_vida_id,
                json_estructurado=datos_ia.model_dump(),
            )
            db.add(nuevo_dato)

        # ── Estado: COMPLETADO ──────────────────────────────────
        hoja.estado_procesamiento = EstadoProcesamiento.COMPLETADO
        hoja.fecha_procesado = datetime.utcnow()
        db.commit()

        logger.info("Extraccion IA completada para hoja_vida_id=%s", hoja_vida_id)

    except Exception as e:
        logger.error(
            "Error en extraccion IA para hoja_vida_id=%s: %s",
            hoja_vida_id, e, exc_info=True
        )
        # Guardar estado ERROR con mensaje para que el usuario sepa qué pasó
        try:
            hoja.estado_procesamiento = EstadoProcesamiento.ERROR
            db.commit()
        except Exception as db_err:
            logger.error("Error actualizando estado a ERROR: %s", db_err)
    finally:
        db.close()


# ── POST /upload ─────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=HojaDeVidaRead,
    summary="Subir Hoja de Vida (PDF)",
    description=(
        "Sube el PDF de la hoja de vida. "
        "Retorna 202 inmediatamente mientras la extracción con IA corre en segundo plano. "
        "Consulta `/mi-hoja` para ver el estado del procesamiento."
    ),
)
async def upload_hoja_de_vida(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Archivo PDF de la hoja de vida"),
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db),
):
    # ── Validación del archivo ──────────────────────────────────
    _validar_archivo(file)

    contenido = await file.read()

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(contenido) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el tamaño máximo de {settings.MAX_FILE_SIZE_MB} MB.",
        )

    if len(contenido) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    # ── Si ya tiene hoja de vida, eliminar la anterior ─────────
    hoja_existente = db.query(HojaDeVida).filter(
        HojaDeVida.aspirante_id == aspirante.id
    ).first()

    if hoja_existente:
        # Eliminar archivo físico anterior si existe
        if os.path.exists(hoja_existente.url_archivo):
            try:
                os.remove(hoja_existente.url_archivo)
            except OSError as e:
                logger.warning("No se pudo eliminar archivo anterior: %s", e)

        # Eliminar datos de IA anteriores
        db.query(DatosExtraidosIA).filter(
            DatosExtraidosIA.hoja_vida_id == hoja_existente.id
        ).delete()

        db.delete(hoja_existente)
        db.commit()

    # ── Guardar archivo en disco ────────────────────────────────
    ruta_archivo, nombre_guardado = _guardar_archivo(
        contenido, str(aspirante.id), file.filename or "hoja_de_vida.pdf"
    )

    # ── Crear registro en BD ────────────────────────────────────
    nueva_hoja = HojaDeVida(
        aspirante_id=aspirante.id,
        nombre_archivo=file.filename or "hoja_de_vida.pdf",
        url_archivo=ruta_archivo,
        tamano_bytes=len(contenido),
        estado_procesamiento=EstadoProcesamiento.PENDIENTE,
    )
    db.add(nueva_hoja)
    db.commit()
    db.refresh(nueva_hoja)

    # ── Programar extracción con IA en background ───────────────
    background_tasks.add_task(
        _procesar_con_ia,
        str(nueva_hoja.id),
        ruta_archivo,
    )

    logger.info(
        "Hoja de vida recibida | aspirante=%s | archivo=%s | %d bytes",
        aspirante.id, nombre_guardado, len(contenido)
    )

    return nueva_hoja


# ── GET /mi-hoja ─────────────────────────────────────────────────

@router.get(
    "/mi-hoja",
    response_model=HojaDeVidaRead,
    summary="Ver estado de mi Hoja de Vida",
    description="Retorna la hoja de vida del aspirante autenticado con el estado del procesamiento.",
)
def get_mi_hoja(
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db),
):
    hoja = db.query(HojaDeVida).filter(
        HojaDeVida.aspirante_id == aspirante.id
    ).first()

    if not hoja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No has subido ninguna Hoja de Vida todavía.",
        )

    return hoja


# ── GET /{id}/datos-ia ───────────────────────────────────────────

@router.get(
    "/{hoja_vida_id}/datos-ia",
    response_model=DatosExtraidosIARead,
    summary="Ver datos extraídos por la IA",
    description=(
        "Retorna los datos estructurados que Gemini extrajo del PDF. "
        "Solo disponible cuando `estado_procesamiento == COMPLETADO`. "
        "Incluye los datos originales de la IA y los validados por el aspirante (si ya validó)."
    ),
)
def get_datos_ia(
    hoja_vida_id: str,
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db),
):
    # Verificar que la hoja pertenece al aspirante autenticado
    hoja = db.query(HojaDeVida).filter(
        HojaDeVida.id == hoja_vida_id,
        HojaDeVida.aspirante_id == aspirante.id,
    ).first()

    if not hoja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de Vida no encontrada.",
        )

    if hoja.estado_procesamiento == EstadoProcesamiento.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="La extracción con IA aún no ha iniciado. Intenta en unos segundos.",
        )

    if hoja.estado_procesamiento == EstadoProcesamiento.PROCESANDO:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="La IA está procesando tu Hoja de Vida. Intenta en unos momentos.",
        )

    if hoja.estado_procesamiento == EstadoProcesamiento.ERROR:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Ocurrió un error al procesar tu Hoja de Vida con IA. "
                "Por favor, elimina el archivo y vuelve a subirlo."
            ),
        )

    datos = db.query(DatosExtraidosIA).filter(
        DatosExtraidosIA.hoja_vida_id == hoja_vida_id
    ).first()

    if not datos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron datos extraídos para esta Hoja de Vida.",
        )

    # Deserializar JSONB → objeto Pydantic para que el response_model funcione
    datos.json_estructurado = DatosExtraidosGemini.model_validate(datos.json_estructurado)
    if datos.json_validado:
        datos.json_validado = DatosExtraidosGemini.model_validate(datos.json_validado)

    return datos


# ── POST /{id}/validar ───────────────────────────────────────────

@router.post(
    "/{hoja_vida_id}/validar",
    response_model=DatosExtraidosIARead,
    summary="Validar y corregir datos extraídos por la IA",
    description=(
        "El aspirante confirma o corrige los datos que la IA extrajo. "
        "Este endpoint guarda el JSON validado y activa `validado_por_aspirante=true`. "
        "Es el paso previo al cálculo del puntaje."
    ),
)
def validar_datos_ia(
    hoja_vida_id: str,
    payload: DatosExtraidosValidar,
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db),
):
    # Verificar propiedad
    hoja = db.query(HojaDeVida).filter(
        HojaDeVida.id == hoja_vida_id,
        HojaDeVida.aspirante_id == aspirante.id,
    ).first()

    if not hoja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de Vida no encontrada.",
        )

    if hoja.estado_procesamiento != EstadoProcesamiento.COMPLETADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo puedes validar datos una vez que el procesamiento haya terminado (COMPLETADO).",
        )

    datos = db.query(DatosExtraidosIA).filter(
        DatosExtraidosIA.hoja_vida_id == hoja_vida_id
    ).first()

    if not datos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datos de IA no encontrados.",
        )

    # Guardar la versión corregida por el aspirante
    datos.json_validado = payload.datos_corregidos.model_dump()
    datos.validado_por_aspirante = True
    datos.fecha_validacion = datetime.utcnow()

    db.commit()
    db.refresh(datos)

    # Deserializar para el response
    datos.json_estructurado = DatosExtraidosGemini.model_validate(datos.json_estructurado)
    datos.json_validado = DatosExtraidosGemini.model_validate(datos.json_validado)

    logger.info(
        "Datos validados por aspirante=%s | hoja_vida_id=%s",
        aspirante.id, hoja_vida_id
    )

    return datos


# ── DELETE /{id} ─────────────────────────────────────────────────

@router.delete(
    "/{hoja_vida_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar Hoja de Vida",
    description="Elimina el PDF y todos los datos extraídos. Permite subir un nuevo archivo.",
)
def eliminar_hoja_de_vida(
    hoja_vida_id: str,
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db),
):
    hoja = db.query(HojaDeVida).filter(
        HojaDeVida.id == hoja_vida_id,
        HojaDeVida.aspirante_id == aspirante.id,
    ).first()

    if not hoja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de Vida no encontrada.",
        )

    # Eliminar archivo físico
    if os.path.exists(hoja.url_archivo):
        try:
            os.remove(hoja.url_archivo)
        except OSError as e:
            logger.warning("No se pudo eliminar el archivo físico: %s", e)

    db.delete(hoja)
    db.commit()

    logger.info("Hoja de vida eliminada | aspirante=%s", aspirante.id)
