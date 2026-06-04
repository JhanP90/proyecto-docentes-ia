# backend/schemas.py
"""
Esquemas Pydantic v2 para el Sistema de Evaluación Docente.

Organización:
  1. Enums (espejo de models.py — single source of truth para la API)
  2. Auth / Token
  3. Usuario / Aspirante / Administrador
  4. HojaDeVida
  5. [GEMINI CONTRACT] DatosExtraidosIA — el esquema más crítico
  6. Soporte
  7. ReglaEvaluacion (Motor de Reglas)
  8. ResultadoEvaluacion
  9. Schemas de respuesta paginada (utilidades)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Annotated

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    UUID4,
    field_validator,
    model_validator,
    ConfigDict,
)

from models import CategoriaRegla, EstadoAdmision, EstadoProcesamiento


# ══════════════════════════════════════════════════════════════════
# 1.  CONFIGURACIÓN BASE
# ══════════════════════════════════════════════════════════════════

class _BaseSchema(BaseModel):
    """
    Schema base con `from_attributes=True` para poder crear instancias
    directamente desde objetos SQLAlchemy (ORM mode).
    """
    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════
# 2.  AUTH / TOKEN
# ══════════════════════════════════════════════════════════════════

class TokenResponse(BaseModel):
    """Respuesta al endpoint de login."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Payload decodificado del JWT."""
    user_id: Optional[UUID4] = None
    tipo_usuario: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
# 3.  USUARIO BASE / ASPIRANTE / ADMINISTRADOR
# ══════════════════════════════════════════════════════════════════

# ── Registro de Aspirante ────────────────────────────────────────

class AspiranteCreate(BaseModel):
    """Datos que el frontend envía al registrar un nuevo aspirante."""
    nombres: Annotated[str, Field(min_length=2, max_length=100)]
    apellidos: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, description="Mínimo 8 caracteres")]
    cedula: Annotated[str, Field(min_length=5, max_length=20, pattern=r"^\d+$")]
    pais: str = "Colombia"
    departamento: Annotated[str, Field(min_length=2, max_length=100)]
    municipio: Annotated[str, Field(min_length=2, max_length=100)]
    telefono: Optional[str] = None


class AspiranteRead(_BaseSchema):
    """Datos del aspirante devueltos por la API (nunca incluye el hash de password)."""
    id: UUID4
    nombres: str
    apellidos: str
    email: str
    cedula: str
    pais: str
    departamento: str
    municipio: str
    telefono: Optional[str]
    estado: EstadoAdmision
    activo: bool
    created_at: datetime


class AspiranteUpdateEstado(BaseModel):
    """Payload para que el admin cambie el estado de admisión de un aspirante."""
    estado: EstadoAdmision


# ── Administrador ────────────────────────────────────────────────

class AdminCreate(BaseModel):
    """Solo un super-admin puede crear otros administradores."""
    nombres: Annotated[str, Field(min_length=2, max_length=100)]
    apellidos: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class AdminRead(_BaseSchema):
    id: UUID4
    nombres: str
    apellidos: str
    email: str
    activo: bool


# ── Login ────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ══════════════════════════════════════════════════════════════════
# 4.  HOJA DE VIDA
# ══════════════════════════════════════════════════════════════════

class HojaDeVidaRead(_BaseSchema):
    id: UUID4
    aspirante_id: UUID4
    nombre_archivo: str
    url_archivo: str
    tamano_bytes: Optional[int]
    estado_procesamiento: EstadoProcesamiento
    fecha_carga: datetime
    fecha_procesado: Optional[datetime]


# ══════════════════════════════════════════════════════════════════
# 5.  CONTRATO CON GEMINI  ← EL MÁS CRÍTICO
#     Estos esquemas definen EXACTAMENTE lo que la IA debe retornar.
#     Se pasan a Gemini mediante `response_schema` en la API call,
#     forzando Structured Output (JSON válido y tipado).
# ══════════════════════════════════════════════════════════════════

# ── Sub-esquemas de ítems individuales ──────────────────────────

class TituloAcademicoIA(BaseModel):
    """Un título académico detectado por la IA."""
    nivel: Annotated[str, Field(
        description="Nivel del título: PREGRADO, ESPECIALIZACION, MAESTRIA, DOCTORADO, POSTDOCTORADO"
    )]
    nombre_titulo: Annotated[str, Field(description="Nombre exacto del programa/título")]
    institucion: Annotated[str, Field(description="Nombre de la institución que lo otorgó")]
    año_graduacion: Annotated[Optional[int], Field(
        default=None,
        ge=1950,
        le=2030,
        description="Año de graduación o grado"
    )]
    pais: str = "Colombia"

    @field_validator("nivel")
    @classmethod
    def nivel_valido(cls, v: str) -> str:
        niveles_validos = {"PREGRADO", "ESPECIALIZACION", "MAESTRIA", "DOCTORADO", "POSTDOCTORADO"}
        v_upper = v.strip().upper()
        if v_upper not in niveles_validos:
            raise ValueError(f"Nivel '{v}' no reconocido. Use uno de: {niveles_validos}")
        return v_upper


class ExperienciaLaboralIA(BaseModel):
    """Un período de experiencia laboral detectado por la IA."""
    cargo: Annotated[str, Field(description="Cargo o rol desempeñado")]
    institucion: Annotated[str, Field(description="Nombre de la organización o institución")]
    tipo: Annotated[str, Field(
        description="Tipo de experiencia: DOCENCIA_UNIVERSITARIA, DOCENCIA_OTRO, INVESTIGACION, PROFESIONAL, OTRO"
    )]
    fecha_inicio: Annotated[str, Field(description="Fecha de inicio en formato YYYY-MM o YYYY")]
    fecha_fin: Annotated[Optional[str], Field(
        default=None,
        description="Fecha de fin en formato YYYY-MM o YYYY. Null si es el cargo actual."
    )]
    años_calculados: Annotated[Optional[float], Field(
        default=None,
        ge=0,
        le=50,
        description="Años de duración calculados por la IA con máximo 2 decimales"
    )]
    es_actual: bool = False

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        tipos_validos = {
            "DOCENCIA_UNIVERSITARIA", "DOCENCIA_OTRO",
            "INVESTIGACION", "PROFESIONAL", "OTRO"
        }
        v_upper = v.strip().upper()
        if v_upper not in tipos_validos:
            raise ValueError(f"Tipo '{v}' inválido. Use uno de: {tipos_validos}")
        return v_upper


class PublicacionIA(BaseModel):
    """Una publicación científica o académica detectada por la IA."""
    tipo: Annotated[str, Field(
        description="Tipo: ARTICULO_A1, ARTICULO_A2, ARTICULO_B, ARTICULO_C, LIBRO, CAPITULO_LIBRO, OTRO"
    )]
    titulo: Annotated[str, Field(description="Título completo de la publicación")]
    revista_o_editorial: Annotated[Optional[str], Field(default=None, description="Nombre de la revista o editorial")]
    año: Annotated[Optional[int], Field(default=None, ge=1900, le=2030, description="Año de publicación")]
    doi_o_isbn: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        tipos_validos = {
            "ARTICULO_A1", "ARTICULO_A2", "ARTICULO_B", "ARTICULO_C",
            "LIBRO", "CAPITULO_LIBRO", "OTRO"
        }
        v_upper = v.strip().upper()
        if v_upper not in tipos_validos:
            raise ValueError(f"Tipo publicación '{v}' inválido.")
        return v_upper


class PonenciaIA(BaseModel):
    """Una ponencia o participación en congreso detectada por la IA."""
    titulo: str
    evento: Annotated[str, Field(description="Nombre del congreso, seminario o evento")]
    tipo: Annotated[str, Field(
        description="PONENCIA_INTERNACIONAL, PONENCIA_NACIONAL, CONFERENCIA_INVITADA, OTRO"
    )]
    año: Optional[int] = None
    pais: Optional[str] = None


class ProyectoInvestigacionIA(BaseModel):
    """Un proyecto de investigación detectado por la IA."""
    titulo: str
    rol: Annotated[str, Field(description="Rol del aspirante: INVESTIGADOR_PRINCIPAL, CO_INVESTIGADOR, AUXILIAR, OTRO")]
    entidad_financiadora: Optional[str] = None
    año_inicio: Optional[int] = None
    año_fin: Optional[int] = None


# ── ESQUEMA RAÍZ — El "contrato" que se le pasa a Gemini ────────

class DatosExtraidosGemini(BaseModel):
    """
    *** ESQUEMA PRINCIPAL DEL CONTRATO CON GEMINI ***

    Este modelo se serializa a JSON Schema y se pasa como `response_schema`
    en la llamada a la API de Gemini. La IA DEBE retornar un JSON que
    respete exactamente esta estructura.

    Si la IA no puede inferir un campo, devuelve null (nunca inventa datos).
    """
    # Datos personales (para pre-llenar el formulario de validación)
    nombre_completo: Annotated[Optional[str], Field(
        default=None,
        description="Nombre completo del aspirante como aparece en el documento"
    )]
    cedula_detectada: Annotated[Optional[str], Field(
        default=None,
        description="Número de cédula o documento de identidad si aparece en el CV"
    )]
    email_detectado: Optional[str] = None
    telefono_detectado: Optional[str] = None

    # Núcleo del análisis
    titulos_academicos: Annotated[list[TituloAcademicoIA], Field(
        default_factory=list,
        description="Lista de todos los títulos académicos encontrados en el CV"
    )]
    experiencia_laboral: Annotated[list[ExperienciaLaboralIA], Field(
        default_factory=list,
        description="Lista de todas las experiencias laborales encontradas"
    )]
    publicaciones: Annotated[list[PublicacionIA], Field(
        default_factory=list,
        description="Lista de publicaciones científicas y académicas"
    )]
    ponencias: Annotated[list[PonenciaIA], Field(
        default_factory=list,
        description="Lista de ponencias y participaciones en eventos académicos"
    )]
    proyectos_investigacion: Annotated[list[ProyectoInvestigacionIA], Field(
        default_factory=list,
        description="Lista de proyectos de investigación"
    )]

    # Totales pre-calculados por la IA (el motor de reglas los verifica/recalcula)
    total_años_experiencia_docente_universitaria: Annotated[float, Field(
        default=0.0,
        ge=0,
        description="Total años de docencia universitaria (suma de experiencia_laboral tipo DOCENCIA_UNIVERSITARIA)"
    )]
    total_años_experiencia_profesional: Annotated[float, Field(
        default=0.0,
        ge=0,
        description="Total años de experiencia profesional no docente"
    )]

    # Meta: la IA indica su nivel de confianza global
    confianza_extraccion: Annotated[float, Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza de 0.0 a 1.0 en la calidad de la extracción"
    )]
    observaciones_ia: Annotated[Optional[str], Field(
        default=None,
        description="Notas del modelo sobre ambigüedades o partes del CV que no pudo interpretar"
    )]


# ── Schemas para la BD ───────────────────────────────────────────

class DatosExtraidosIARead(_BaseSchema):
    """Respuesta de la API al consultar los datos extraídos por IA."""
    id: UUID4
    hoja_vida_id: UUID4
    json_estructurado: DatosExtraidosGemini        # ya deserializado, no string crudo
    json_validado: Optional[DatosExtraidosGemini]  # None hasta que el aspirante valide
    validado_por_aspirante: bool
    fecha_validacion: Optional[datetime]
    created_at: datetime


class DatosExtraidosValidar(BaseModel):
    """
    Payload que envía el frontend cuando el aspirante confirma/corrige
    los datos en la vista split-screen.
    """
    datos_corregidos: DatosExtraidosGemini


# ══════════════════════════════════════════════════════════════════
# 6.  SOPORTE (archivos de evidencia)
# ══════════════════════════════════════════════════════════════════

class SoporteRead(_BaseSchema):
    id: UUID4
    aspirante_id: UUID4
    categoria: CategoriaRegla
    nombre_item: str
    descripcion: Optional[str]
    url_archivo: str
    verificado: bool
    fecha_carga: datetime


# ══════════════════════════════════════════════════════════════════
# 7.  MOTOR DE REGLAS (CRUD para administradores)
# ══════════════════════════════════════════════════════════════════

class ReglaEvaluacionCreate(BaseModel):
    categoria: CategoriaRegla
    nombre_item: Annotated[str, Field(min_length=3, max_length=255)]
    descripcion: Optional[str] = None
    puntos_por_item: Annotated[float, Field(gt=0, le=150)]
    tope_maximo_categoria: Annotated[float, Field(gt=0, le=150)]
    unidad: Optional[str] = None  # Ej: "AÑO", "ARTICULO", "PONENCIA"
    activo: bool = True


class ReglaEvaluacionUpdate(BaseModel):
    """Todos los campos son opcionales para soportar PATCH parcial."""
    nombre_item: Optional[str] = None
    descripcion: Optional[str] = None
    puntos_por_item: Optional[Annotated[float, Field(gt=0, le=150)]] = None
    tope_maximo_categoria: Optional[Annotated[float, Field(gt=0, le=150)]] = None
    unidad: Optional[str] = None
    activo: Optional[bool] = None


class ReglaEvaluacionRead(_BaseSchema):
    id: UUID4
    categoria: CategoriaRegla
    nombre_item: str
    descripcion: Optional[str]
    puntos_por_item: float
    tope_maximo_categoria: float
    unidad: Optional[str]
    activo: bool
    created_at: datetime
    updated_at: datetime


# ══════════════════════════════════════════════════════════════════
# 8.  RESULTADO DE EVALUACIÓN
# ══════════════════════════════════════════════════════════════════

class ResultadoEvaluacionRead(_BaseSchema):
    id: UUID4
    aspirante_id: UUID4
    puntaje_total: float
    # Desglose por categoría tal como se guardó en JSONB
    desglose_puntaje: Optional[dict[str, float]]
    fecha_calculo: datetime
    recalculado: bool


# ══════════════════════════════════════════════════════════════════
# 9.  SCHEMAS DE RESPUESTA PAGINADA (utilidades reutilizables)
# ══════════════════════════════════════════════════════════════════

class PaginatedResponse(_BaseSchema):
    """Wrapper genérico para respuestas paginadas del dashboard admin."""
    total: int
    pagina: int
    por_pagina: int
    items: list  # El router lo especializa con el tipo correcto


class AspiranteRankingItem(_BaseSchema):
    """Fila del ranking de aspirantes en el dashboard del admin."""
    id: UUID4
    nombres: str
    apellidos: str
    email: str
    cedula: str
    estado: EstadoAdmision
    puntaje_total: Optional[float] = None
    desglose_puntaje: Optional[dict[str, float]] = None
    fecha_calculo: Optional[datetime] = None
    hoja_vida_estado: Optional[EstadoProcesamiento] = None
