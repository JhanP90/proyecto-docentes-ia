# backend/models.py
"""
Modelos SQLAlchemy para el Sistema de Evaluación Docente - Universidad de Caldas.

Patrón de herencia: JOINED TABLE INHERITANCE
  - `usuarios` → tabla base con los campos comunes.
  - `aspirantes_detalles` → extensión con campos propios del aspirante.
  - `Administrador` no necesita tabla extra (no tiene campos adicionales).
"""
import enum
import uuid
import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    ForeignKey, Enum as SAEnum, DateTime, Text, JSON, Uuid
)
from sqlalchemy.orm import relationship

from database import Base


# ──────────────────────────────────────────────
# ENUMERACIONES (sincronizadas con Pydantic)
# ──────────────────────────────────────────────

class EstadoAdmision(str, enum.Enum):
    ENVIADO     = "ENVIADO"
    EN_PROCESO  = "EN_PROCESO"
    EVALUADO    = "EVALUADO"
    ACEPTADO    = "ACEPTADO"
    RECHAZADO   = "RECHAZADO"


class CategoriaRegla(str, enum.Enum):
    EXPERIENCIA   = "EXPERIENCIA"   # Máx 20 pts
    FORMACION     = "FORMACION"     # Máx 40 pts
    PRODUCCION    = "PRODUCCION"    # Máx 50 pts
    PONENCIAS     = "PONENCIAS"     # Máx 10 pts
    INVESTIGACION = "INVESTIGACION" # Máx 20 pts
    PREMIOS       = "PREMIOS"       # Máx 10 pts


class EstadoProcesamiento(str, enum.Enum):
    PENDIENTE   = "PENDIENTE"
    PROCESANDO  = "PROCESANDO"
    COMPLETADO  = "COMPLETADO"
    ERROR       = "ERROR"


# ──────────────────────────────────────────────
# HERENCIA DE USUARIOS (Joined Table)
# ──────────────────────────────────────────────

class Usuario(Base):
    """
    Tabla base. Almacena la identidad común de cualquier usuario del sistema.
    El discriminador `tipo_usuario` activa el polimorfismo de SQLAlchemy.
    """
    __tablename__ = "usuarios"

    id            = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombres       = Column(String(100), nullable=False)
    apellidos     = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    tipo_usuario  = Column(String(20), nullable=False)  # discriminador
    activo        = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at    = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    __mapper_args__ = {
        "polymorphic_on": tipo_usuario,
        "polymorphic_identity": "usuario",
    }


class Administrador(Usuario):
    """
    Perfil administrador. No requiere tabla propia porque no agrega campos.
    El polimorfismo se maneja sólo con el discriminador de `usuarios`.
    """
    __mapper_args__ = {"polymorphic_identity": "admin"}


class Aspirante(Usuario):
    """
    Perfil aspirante. Extiende `usuarios` con campos de identificación y geo.
    """
    __tablename__ = "aspirantes_detalles"

    id            = Column(Uuid(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True)
    cedula        = Column(String(20), unique=True, nullable=False, index=True)
    pais          = Column(String(100), nullable=False, default="Colombia")
    departamento  = Column(String(100), nullable=False)
    municipio     = Column(String(100), nullable=False)
    telefono      = Column(String(20), nullable=True)
    estado        = Column(
        SAEnum(EstadoAdmision, name="estado_admision"),
        default=EstadoAdmision.ENVIADO,
        nullable=False,
    )

    __mapper_args__ = {"polymorphic_identity": "aspirante"}

    # ── Relaciones ──────────────────────────────
    hoja_vida  = relationship("HojaDeVida", back_populates="aspirante", uselist=False)
    soportes   = relationship("Soporte", back_populates="aspirante", cascade="all, delete-orphan")
    resultado  = relationship("ResultadoEvaluacion", back_populates="aspirante", uselist=False)


# ──────────────────────────────────────────────
# ARCHIVOS E INTELIGENCIA ARTIFICIAL
# ──────────────────────────────────────────────

class HojaDeVida(Base):
    """
    Representa el PDF cargado por el aspirante.
    `estado_procesamiento` controla el ciclo de vida del análisis con IA.
    """
    __tablename__ = "hojas_vida"

    id             = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aspirante_id   = Column(Uuid(as_uuid=True), ForeignKey("aspirantes_detalles.id"), unique=True, nullable=False)
    nombre_archivo = Column(String(255), nullable=False)  # nombre original del archivo
    url_archivo    = Column(String(500), nullable=False)   # ruta relativa en servidor o URL en cloud
    tamano_bytes   = Column(Integer, nullable=True)
    estado_procesamiento = Column(
        SAEnum(EstadoProcesamiento, name="estado_procesamiento"),
        default=EstadoProcesamiento.PENDIENTE,
        nullable=False,
    )
    fecha_carga    = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    fecha_procesado = Column(DateTime, nullable=True)  # se llena cuando la IA termina

    # ── Relaciones ──────────────────────────────
    aspirante      = relationship("Aspirante", back_populates="hoja_vida")
    datos_extraidos = relationship("DatosExtraidosIA", back_populates="hoja_vida", uselist=False)


class DatosExtraidosIA(Base):
    """
    Almacena el JSON estructurado que retorna Gemini, validado por Pydantic.
    Usamos JSON para poder hacer queries sobre el contenido del JSON.
    `validado_por_aspirante` se activa cuando el aspirante confirma/corrige los datos en el split-screen.
    """
    __tablename__ = "datos_extraidos_ia"

    id              = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hoja_vida_id    = Column(Uuid(as_uuid=True), ForeignKey("hojas_vida.id"), unique=True, nullable=False)
    # JSON es indexable y consultable
    json_estructurado = Column(JSON, nullable=False)
    # Snapshot de los datos DESPUÉS de que el aspirante los corrigió/validó
    json_validado   = Column(JSON, nullable=True)
    validado_por_aspirante = Column(Boolean, default=False, nullable=False)
    fecha_validacion = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # ── Relaciones ──────────────────────────────
    hoja_vida = relationship("HojaDeVida", back_populates="datos_extraidos")


class Soporte(Base):
    """
    Archivos adjuntos que el aspirante sube como evidencia de un ítem específico.
    Ej: el PDF del diploma de doctorado, o el certificado de una publicación.
    """
    __tablename__ = "soportes"

    id           = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aspirante_id = Column(Uuid(as_uuid=True), ForeignKey("aspirantes_detalles.id"), nullable=False)
    categoria    = Column(SAEnum(CategoriaRegla, name="categoria_regla"), nullable=False)
    nombre_item  = Column(String(255), nullable=False)   # Ej: "Doctorado en IA"
    descripcion  = Column(Text, nullable=True)
    url_archivo  = Column(String(500), nullable=False)
    verificado   = Column(Boolean, default=False, nullable=False)
    fecha_carga  = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # ── Relaciones ──────────────────────────────
    aspirante = relationship("Aspirante", back_populates="soportes")


# ──────────────────────────────────────────────
# MOTOR DE REGLAS DINÁMICO
# ──────────────────────────────────────────────

class ReglaEvaluacion(Base):
    """
    Catálogo configurable de reglas de puntuación.
    Los administradores pueden modificar `puntos_por_item` y `tope_maximo_categoria`
    sin tocar el código — el motor de cálculo siempre lee de esta tabla.

    Ejemplo de datos:
      categoria=FORMACION, nombre_item="Doctorado", puntos_por_item=40.0, tope_maximo_categoria=40.0
      categoria=EXPERIENCIA, nombre_item="Año docente universidad", puntos_por_item=2.0, tope_maximo_categoria=20.0
    """
    __tablename__ = "reglas_evaluacion"

    id                     = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria              = Column(SAEnum(CategoriaRegla, name="categoria_regla_eval"), nullable=False)
    nombre_item            = Column(String(255), nullable=False)
    descripcion            = Column(Text, nullable=True)
    puntos_por_item        = Column(Float, nullable=False)
    tope_maximo_categoria  = Column(Float, nullable=False)
    # `unidad` permite escalar: ej. "AÑO" → el motor multiplica puntos × años
    unidad                 = Column(String(50), nullable=True)  # "AÑO", "ARTICULO", "PONENCIA", etc.
    activo                 = Column(Boolean, default=True, nullable=False)
    created_at             = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at             = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


class ResultadoEvaluacion(Base):
    """
    Resultado final del cálculo para un aspirante.
    `desglose_puntaje` guarda el detalle categoría-por-categoría como JSON,
    lo que permite mostrar un resumen transparente al aspirante y al admin.
    """
    __tablename__ = "resultados_evaluacion"

    id              = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aspirante_id    = Column(Uuid(as_uuid=True), ForeignKey("aspirantes_detalles.id"), unique=True, nullable=False)
    puntaje_total   = Column(Float, default=0.0, nullable=False)
    # Ej: {"FORMACION": 38.0, "EXPERIENCIA": 14.0, "PRODUCCION": 45.0, ...}
    desglose_puntaje = Column(JSON, nullable=False)
    fecha_calculo   = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    recalculado     = Column(Boolean, default=False, nullable=False)  # True si fue recalculado tras corrección

    # ── Relaciones ──────────────────────────────
    aspirante = relationship("Aspirante", back_populates="resultado")