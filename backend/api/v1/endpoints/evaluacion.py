import uuid
# backend/api/v1/endpoints/evaluacion.py
"""
Router para la evaluación y cálculo de puntajes.

Endpoints:
  POST /api/v1/evaluacion/calcular           → Calcula o recalcula el puntaje del aspirante autenticado.
  POST /api/v1/evaluacion/calcular/{id}      → (Admin) Calcula el puntaje de un aspirante específico.
  GET  /api/v1/evaluacion/resultado          → Obtiene el resultado del aspirante autenticado.
  GET  /api/v1/evaluacion/resultado/{id}     → (Admin) Obtiene el resultado de un aspirante específico.
  POST /api/v1/evaluacion/inicializar-reglas → Crea las reglas por defecto si la tabla está vacía.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Aspirante, Administrador, ResultadoEvaluacion
from schemas import ResultadoEvaluacionRead
from core.dependencies import get_current_user, require_aspirante, require_admin
from services.evaluacion_service import calcular_puntaje_aspirante, inicializar_reglas_por_defecto

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Endpoints para Aspirantes ---

@router.post(
    "/calcular",
    response_model=ResultadoEvaluacionRead,
    summary="Calcular mi puntaje",
    description="Calcula el puntaje final basado en los datos de IA y las reglas actuales."
)
def calcular_mi_puntaje(
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db)
):
    try:
        resultado = calcular_puntaje_aspirante(db, aspirante_id=str(aspirante.id))
        return resultado
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/resultado",
    response_model=ResultadoEvaluacionRead,
    summary="Ver mi resultado de evaluación",
    description="Retorna el puntaje total y el desglose por categorías."
)
def get_mi_resultado(
    aspirante: Aspirante = Depends(require_aspirante),
    db: Session = Depends(get_db)
):
    resultado = db.query(ResultadoEvaluacion).filter(
        ResultadoEvaluacion.aspirante_id == aspirante.id
    ).first()

    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no se ha calculado tu puntaje de evaluación."
        )

    return resultado


# --- Endpoints para Administradores ---

@router.post(
    "/calcular/{aspirante_id}",
    response_model=ResultadoEvaluacionRead,
    summary="Calcular puntaje de un aspirante (Admin)",
    description="Fuerza el cálculo o recálculo del puntaje de un aspirante específico."
)
def calcular_puntaje_admin(
    aspirante_id: str,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        resultado = calcular_puntaje_aspirante(db, aspirante_id=aspirante_id)
        return resultado
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/resultado/{aspirante_id}",
    response_model=ResultadoEvaluacionRead,
    summary="Ver resultado de un aspirante (Admin)",
)
def get_resultado_admin(
    aspirante_id: str,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    resultado = db.query(ResultadoEvaluacion).filter(
        ResultadoEvaluacion.aspirante_id == aspirante_id
    ).first()

    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El aspirante no tiene un resultado calculado."
        )

    return resultado


@router.post(
    "/inicializar-reglas",
    status_code=status.HTTP_201_CREATED,
    summary="Inicializar reglas por defecto (Admin/Setup)",
    description="Puebla la tabla de reglas con los valores base si está vacía."
)
def inicializar_reglas(
    # Nota: Temporalmente sin restricción de admin estricta para facilitar setup, 
    # en prod debería requerir admin.
    db: Session = Depends(get_db)
):
    inicializar_reglas_por_defecto(db)
    return {"mensaje": "Reglas inicializadas o ya existían"}
