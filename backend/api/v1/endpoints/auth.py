# backend/api/v1/endpoints/auth.py
"""
Router de autenticación.

Endpoints:
  POST /api/v1/auth/register  → Registro de aspirante
  POST /api/v1/auth/login     → Login (devuelve JWT)
  GET  /api/v1/auth/me        → Perfil del usuario autenticado

Notas de diseño:
  - El login usa `OAuth2PasswordRequestForm` (estándar OAuth2 que Swagger
    entiende directamente, sin configuración extra).
  - El registro es exclusivo para Aspirantes. Los Administradores se crean
    por un endpoint separado en el router de admin (con autenticación previa).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Aspirante
from schemas import (
    AspiranteCreate,
    AspiranteRead,
    LoginRequest,
    TokenResponse,
)
from core.security import hash_password, verify_password, create_access_token
from core.dependencies import get_current_user

router = APIRouter()


# ── POST /register ───────────────────────────────────────────────

@router.post(
    "/register",
    response_model=AspiranteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo aspirante",
    description=(
        "Crea una cuenta de aspirante. "
        "Valida que el email y la cédula no estén ya registrados."
    ),
)
def register_aspirante(payload: AspiranteCreate, db: Session = Depends(get_db)):
    # ── Unicidad de email ────────────────────────────────────────
    if db.query(Usuario).filter(Usuario.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{payload.email}' ya está registrado.",
        )

    # ── Unicidad de cédula ───────────────────────────────────────
    if db.query(Aspirante).filter(Aspirante.cedula == payload.cedula).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La cédula '{payload.cedula}' ya está registrada.",
        )

    # ── Creación del objeto ──────────────────────────────────────
    nuevo_aspirante = Aspirante(
        nombres=payload.nombres.strip().title(),
        apellidos=payload.apellidos.strip().title(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        cedula=payload.cedula.strip(),
        pais=payload.pais,
        departamento=payload.departamento.strip().title(),
        municipio=payload.municipio.strip().title(),
        telefono=payload.telefono,
    )

    db.add(nuevo_aspirante)
    db.commit()
    db.refresh(nuevo_aspirante)

    return nuevo_aspirante


# ── POST /login ──────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description=(
        "Autentica con email y password. "
        "Retorna un JWT Bearer token con expiración configurable."
    ),
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Usa OAuth2PasswordRequestForm para compatibilidad con el botón
    'Authorize' de Swagger UI — el campo `username` equivale al email.
    """
    # ── Buscar usuario ───────────────────────────────────────────
    user = db.query(Usuario).filter(
        Usuario.email == form_data.username.strip().lower()
    ).first()

    # Mensaje genérico intencionalmente — no revelar si el email existe
    _auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user:
        raise _auth_error

    if not verify_password(form_data.password, user.password_hash):
        raise _auth_error

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva. Contacta al administrador.",
        )

    # ── Generar token ────────────────────────────────────────────
    token = create_access_token(
        subject=str(user.id),
        tipo_usuario=user.tipo_usuario,
    )

    return TokenResponse(access_token=token)


# ── GET /me ──────────────────────────────────────────────────────

@router.get(
    "/me",
    summary="Perfil del usuario autenticado",
    description="Requiere JWT válido en el header Authorization.",
)
def get_me(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna los datos del usuario que está haciendo la petición.
    Maneja tanto aspirantes como administradores.
    """
    base = {
        "id": str(current_user.id),
        "nombres": current_user.nombres,
        "apellidos": current_user.apellidos,
        "email": current_user.email,
        "tipo_usuario": current_user.tipo_usuario,
        "activo": current_user.activo,
        "created_at": current_user.created_at.isoformat(),
    }
    # Si es aspirante, agregar campos extra
    if current_user.tipo_usuario == "aspirante":
        base.update({
            "cedula": current_user.cedula,
            "pais": current_user.pais,
            "departamento": current_user.departamento,
            "municipio": current_user.municipio,
            "telefono": current_user.telefono,
            "estado": current_user.estado.value if current_user.estado else None,
        })
    return base
