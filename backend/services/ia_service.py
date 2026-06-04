# backend/services/ia_service.py
"""
Servicio de extracción estructurada con Google Gemini.

Flujo:
  1. Recibe el texto plano del CV (extraído por pdf_service).
  2. Construye un prompt de sistema detallado que instruye a Gemini.
  3. Llama a la API de Gemini con `response_mime_type="application/json"`
     y `response_schema=DatosExtraidosGemini` (Structured Output).
  4. Pydantic valida y deserializa la respuesta → garantiza tipos exactos.
  5. Retorna el objeto `DatosExtraidosGemini` listo para guardar en BD.

NOTA SOBRE STRUCTURED OUTPUT:
  Gemini Structured Output (response_schema) garantiza que la respuesta
  sea JSON válido que respete el schema de Pydantic. Elimina la necesidad
  de parsear texto libre o manejar alucinaciones de formato.
"""
import json
import logging
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from core.config import settings
from schemas import DatosExtraidosGemini

logger = logging.getLogger(__name__)


# ── Configuración del cliente Gemini ────────────────────────────
def _get_model() -> genai.GenerativeModel:
    """
    Inicializa el modelo de Gemini con la configuración de Structured Output.
    Se llama en cada request para que la API key pueda recargarse desde .env
    sin reiniciar el servidor (útil en desarrollo).
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY no configurada. "
            "Agrega tu clave en el archivo .env"
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Obtenemos el schema para forzar a la IA
    schema_json = json.dumps(DatosExtraidosGemini.model_json_schema(), indent=2)
    prompt_completo = _SYSTEM_PROMPT + "\n\nDEBES RESPONDER EXCLUSIVAMENTE CON UN JSON VÁLIDO QUE CUMPLA ESTE SCHEMA (NO USES MARKDOWN):\n" + schema_json

    return genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        generation_config=GenerationConfig(
            # Forzamos a que solo devuelva JSON
            response_mime_type="application/json",
            temperature=0.0,    # 0.0 = determinista, sin creatividad — queremos datos, no texto
            max_output_tokens=8192,
        ),
        system_instruction=prompt_completo,
    )


# ── Prompt del sistema ───────────────────────────────────────────
_SYSTEM_PROMPT = """
Eres un extractor experto de información académica y laboral de Hojas de Vida (CVs) universitarios en Colombia.

Tu única tarea es analizar el texto del CV y extraer la información de forma ESTRUCTURADA y PRECISA.

REGLAS CRÍTICAS:
1. NUNCA inventes información que no esté explícita en el texto.
2. Si no puedes determinar un valor con certeza, usa `null`.
3. Para los años de experiencia, calcula la duración en años con máximo 2 decimales (ej: 2.5 años).
4. Normaliza los niveles académicos: PREGRADO, ESPECIALIZACION, MAESTRIA, DOCTORADO, POSTDOCTORADO.
5. Para experiencia laboral, clasifica el tipo:
   - DOCENCIA_UNIVERSITARIA: docente en universidad o institución de educación superior.
   - DOCENCIA_OTRO: docente en colegio, instituto técnico, etc.
   - INVESTIGACION: investigador en grupo, centro o proyecto de investigación.
   - PROFESIONAL: trabajo profesional no docente (consultor, gerente, etc.).
   - OTRO: cualquier otro tipo de experiencia.
6. Para publicaciones, clasifica según el sistema de indexación colombiano Minciencias:
   - ARTICULO_A1: revista Q1/Q2 en Scopus/WoS, o categoría A1 en Minciencias.
   - ARTICULO_A2: revista Q3 en Scopus/WoS, o categoría A2 en Minciencias.
   - ARTICULO_B: categoría B en Minciencias.
   - ARTICULO_C: categoría C en Minciencias.
   - Si no hay clasificación clara, usa OTRO.
7. La confianza_extraccion debe reflejar qué tan completo y legible estaba el documento:
   - 0.9-1.0: CV bien estructurado, información clara.
   - 0.6-0.8: CV con algunas ambigüedades o falta de fechas.
   - 0.0-0.5: CV escaneado, mal formateado, o con texto confuso.
8. Responde ÚNICAMENTE con el JSON estructurado. Sin texto adicional, sin explicaciones.
""".strip()


def _construir_prompt_usuario(texto_cv: str) -> str:
    """
    Construye el prompt del usuario que incluye el texto del CV.
    Limita el texto a ~30.000 caracteres para no exceder la ventana de contexto
    en documentos extremadamente largos.
    """
    MAX_CHARS = 30_000
    texto_truncado = texto_cv[:MAX_CHARS]
    fue_truncado = len(texto_cv) > MAX_CHARS

    nota_truncado = (
        "\n\n[NOTA: El documento fue truncado a 30.000 caracteres por longitud excesiva. "
        "Extrae la información disponible en este fragmento.]\n"
        if fue_truncado else ""
    )

    return (
        f"Analiza el siguiente CV y extrae toda la información estructurada:\n\n"
        f"{texto_truncado}"
        f"{nota_truncado}"
    )


# ── Función principal ────────────────────────────────────────────

def extraer_datos_cv(texto_cv: str) -> DatosExtraidosGemini:
    """
    Extrae datos estructurados de un CV usando Gemini Structured Output.

    Args:
        texto_cv: Texto plano extraído del PDF por pdf_service.

    Returns:
        DatosExtraidosGemini validado por Pydantic — garantiza tipos exactos.

    Raises:
        ValueError: Si la API key no está configurada.
        RuntimeError: Si Gemini retorna una respuesta vacía o inválida.
        Exception: Re-lanza cualquier error de la API de Google.
    """
    if not texto_cv or not texto_cv.strip():
        logger.warning("Texto del CV vacío — retornando datos en blanco con confianza 0.0")
        return DatosExtraidosGemini(
            confianza_extraccion=0.0,
            observaciones_ia=(
                "El PDF no contenía texto extraíble. "
                "Puede ser un documento escaneado. "
                "Se requiere validación manual completa."
            ),
        )

    model = _get_model()
    prompt = _construir_prompt_usuario(texto_cv)

    logger.info(
        "Enviando CV a Gemini (%s) | %d caracteres",
        settings.GEMINI_MODEL, len(texto_cv)
    )

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        logger.error("Error llamando a la API de Gemini: %s", e)
        raise RuntimeError(f"Error al conectar con la API de Gemini: {e}") from e

    # Verificar que la respuesta no esté bloqueada por safety filters
    if not response.candidates:
        raise RuntimeError(
            "Gemini no retornó candidatos. "
            "El documento puede haber sido bloqueado por filtros de seguridad."
        )

    texto_respuesta = response.text

    if not texto_respuesta or not texto_respuesta.strip():
        raise RuntimeError("Gemini retornó una respuesta vacía.")

    logger.info("Respuesta de Gemini recibida | %d caracteres", len(texto_respuesta))

    # Con Structured Output, response.text ya es JSON válido.
    # Pydantic hace la validación final — si hay discrepancias de tipo, lanza ValidationError.
    try:
        datos = DatosExtraidosGemini.model_validate_json(texto_respuesta)
    except Exception as e:
        logger.error(
            "La respuesta de Gemini no pasó validación Pydantic: %s\nRespuesta: %s",
            e, texto_respuesta[:500]
        )
        raise RuntimeError(
            f"La respuesta de Gemini no coincide con el schema esperado: {e}"
        ) from e

    logger.info(
        "Extraccion exitosa | titulos=%d | experiencias=%d | publicaciones=%d | confianza=%.2f",
        len(datos.titulos_academicos),
        len(datos.experiencia_laboral),
        len(datos.publicaciones),
        datos.confianza_extraccion,
    )

    return datos


def extraer_datos_cv_mock() -> DatosExtraidosGemini:
    """
    Retorna datos de ejemplo para desarrollo sin necesidad de GEMINI_API_KEY.
    Úsalo mientras configuras la clave real.
    """
    from schemas import (
        TituloAcademicoIA, ExperienciaLaboralIA, PublicacionIA
    )
    return DatosExtraidosGemini(
        nombre_completo="Juan Carlos Pérez Gómez",
        cedula_detectada="12345678",
        email_detectado="juanperez@ucaldas.edu.co",
        titulos_academicos=[
            TituloAcademicoIA(
                nivel="DOCTORADO",
                nombre_titulo="Doctorado en Ciencias de la Computación",
                institucion="Universidad Nacional de Colombia",
                año_graduacion=2015,
                pais="Colombia",
            ),
            TituloAcademicoIA(
                nivel="MAESTRIA",
                nombre_titulo="Maestría en Inteligencia Artificial",
                institucion="Universidad de Antioquia",
                año_graduacion=2010,
                pais="Colombia",
            ),
        ],
        experiencia_laboral=[
            ExperienciaLaboralIA(
                cargo="Profesor Asociado",
                institucion="Universidad de Caldas",
                tipo="DOCENCIA_UNIVERSITARIA",
                fecha_inicio="2016-01",
                fecha_fin=None,
                años_calculados=8.5,
                es_actual=True,
            ),
        ],
        publicaciones=[
            PublicacionIA(
                tipo="ARTICULO_A1",
                titulo="Deep Learning Applications in Education Assessment",
                revista_o_editorial="IEEE Transactions on Learning Technologies",
                año=2022,
                doi_o_isbn="10.1109/TLT.2022.12345",
            ),
        ],
        total_años_experiencia_docente_universitaria=8.5,
        total_años_experiencia_profesional=0.0,
        confianza_extraccion=0.95,
        observaciones_ia="Datos de ejemplo para desarrollo. Reemplazar con GEMINI_API_KEY real.",
    )
