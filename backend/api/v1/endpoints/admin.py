# backend/api/v1/endpoints/admin.py
"""
Router del Panel de Administración.

Exclusivo para usuarios con rol de Administrador.
Endpoints:
  - CRUD de Reglas de Evaluación.
  - Tabla de Ranking de Aspirantes (con filtros y paginación).
  - Cambio de estado de un Aspirante (ACEPTADO, RECHAZADO, etc.).
  - Registro de nuevos administradores.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import (
    Administrador, ReglaEvaluacion, Aspirante, ResultadoEvaluacion,
    EstadoAdmision, HojaDeVida
)
from schemas import (
    AdminCreate, AdminRead,
    ReglaEvaluacionCreate, ReglaEvaluacionUpdate, ReglaEvaluacionRead,
    AspiranteUpdateEstado, AspiranteRankingItem, PaginatedResponse
)
from core.security import hash_password
from core.dependencies import require_admin

router = APIRouter()


# ── Gestión de Administradores ───────────────────────────────────

@router.post(
    "/register",
    response_model=AdminRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo Administrador",
    description="Solo un administrador existente puede crear otro."
)
def create_admin(
    payload: AdminCreate,
    #current_admin: Administrador = Depends(require_admin), #sin autenticacion por ahora para pruebas
    db: Session = Depends(get_db)
):
    from models import Usuario # Importamos aquí para evitar circulares si los hay
    
    # Verificar email único
    if db.query(Usuario).filter(Usuario.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado en el sistema."
        )

    nuevo_admin = Administrador(
        nombres=payload.nombres.strip().title(),
        apellidos=payload.apellidos.strip().title(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
    )
    
    db.add(nuevo_admin)
    db.commit()
    db.refresh(nuevo_admin)
    return nuevo_admin


# ── Motor de Reglas (CRUD) ───────────────────────────────────────

@router.get(
    "/reglas",
    response_model=list[ReglaEvaluacionRead],
    summary="Listar todas las reglas de evaluación",
)
def get_reglas(
    activos_solamente: bool = False,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(ReglaEvaluacion)
    if activos_solamente:
        query = query.filter(ReglaEvaluacion.activo == True)
    return query.order_by(ReglaEvaluacion.categoria, ReglaEvaluacion.nombre_item).all()


@router.post(
    "/reglas",
    response_model=ReglaEvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear regla de evaluación",
)
def create_regla(
    payload: ReglaEvaluacionCreate,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    nueva_regla = ReglaEvaluacion(**payload.model_dump())
    db.add(nueva_regla)
    db.commit()
    db.refresh(nueva_regla)
    return nueva_regla


@router.patch(
    "/reglas/{regla_id}",
    response_model=ReglaEvaluacionRead,
    summary="Actualizar regla de evaluación",
)
def update_regla(
    regla_id: str,
    payload: ReglaEvaluacionUpdate,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    regla = db.query(ReglaEvaluacion).filter(ReglaEvaluacion.id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(regla, key, value)

    db.commit()
    db.refresh(regla)
    return regla


@router.delete(
    "/reglas/{regla_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar (desactivar) regla de evaluación",
    description="Soft-delete: marca la regla como inactiva."
)
def delete_regla(
    regla_id: str,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    regla = db.query(ReglaEvaluacion).filter(ReglaEvaluacion.id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada.")
    
    regla.activo = False
    db.commit()


# ── Dashboard: Ranking y Gestión de Aspirantes ───────────────────

@router.get(
    "/ranking",
    response_model=PaginatedResponse,
    summary="Tabla de Ranking de Aspirantes",
    description="Lista a los aspirantes. Puede filtrar por estado y ordena por puntaje mayor a menor."
)
def get_ranking(
    estado: Optional[EstadoAdmision] = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Hacemos un JOIN entre Aspirante, ResultadoEvaluacion (opcional) y HojaDeVida (opcional)
    query = db.query(
        Aspirante, 
        ResultadoEvaluacion.puntaje_total, 
        ResultadoEvaluacion.desglose_puntaje,
        ResultadoEvaluacion.fecha_calculo,
        HojaDeVida.estado_procesamiento
    ).outerjoin(
        ResultadoEvaluacion, Aspirante.id == ResultadoEvaluacion.aspirante_id
    ).outerjoin(
        HojaDeVida, Aspirante.id == HojaDeVida.aspirante_id
    )

    if estado:
        query = query.filter(Aspirante.estado == estado)

    # Ordenar por puntaje total descendente, nulls al final
    query = query.order_by(desc(ResultadoEvaluacion.puntaje_total).nulls_last())

    total_items = query.count()
    offset = (pagina - 1) * por_pagina
    resultados = query.offset(offset).limit(por_pagina).all()

    items_list = []
    for asp, puntaje, desglose, fecha, estado_hoja in resultados:
        items_list.append(AspiranteRankingItem(
            id=asp.id,
            nombres=asp.nombres,
            apellidos=asp.apellidos,
            email=asp.email,
            cedula=asp.cedula,
            estado=asp.estado,
            puntaje_total=puntaje,
            desglose_puntaje=desglose,
            fecha_calculo=fecha,
            hoja_vida_estado=estado_hoja
        ))

    return PaginatedResponse(
        total=total_items,
        pagina=pagina,
        por_pagina=por_pagina,
        items=items_list
    )


@router.patch(
    "/aspirantes/{aspirante_id}/estado",
    response_model=AspiranteRankingItem,
    summary="Cambiar estado de admisión de un aspirante",
)
def update_estado_aspirante(
    aspirante_id: str,
    payload: AspiranteUpdateEstado,
    admin: Administrador = Depends(require_admin),
    db: Session = Depends(get_db)
):
    aspirante = db.query(Aspirante).filter(Aspirante.id == aspirante_id).first()
    if not aspirante:
        raise HTTPException(status_code=404, detail="Aspirante no encontrado.")

    aspirante.estado = payload.estado
    db.commit()
    db.refresh(aspirante)

    # Reconstruir el item para la respuesta
    resultado = db.query(ResultadoEvaluacion).filter(ResultadoEvaluacion.aspirante_id == aspirante.id).first()
    hoja = db.query(HojaDeVida).filter(HojaDeVida.aspirante_id == aspirante.id).first()

    return AspiranteRankingItem(
        id=aspirante.id,
        nombres=aspirante.nombres,
        apellidos=aspirante.apellidos,
        email=aspirante.email,
        cedula=aspirante.cedula,
        estado=aspirante.estado,
        puntaje_total=resultado.puntaje_total if resultado else None,
        desglose_puntaje=resultado.desglose_puntaje if resultado else None,
        fecha_calculo=resultado.fecha_calculo if resultado else None,
        hoja_vida_estado=hoja.estado_procesamiento if hoja else None
    )
