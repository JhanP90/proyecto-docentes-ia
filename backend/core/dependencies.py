# backend/core/dependencies.py
"""
Dependencias reutilizables de FastAPI (Depends).

La dependencia `get_current_user` es el pilar de la autenticación:
  - Se importa en cualquier router que necesite proteger un endpoint.
  - `require_admin` y `require_aspirante` son variantes especializadas.

Uso en un endpoint:
    @router.get("/mi-perfil")
    def mi_perfil(current_user: Usuario = Depends(get_current_user)):
        ...

    @router.get("/solo-admin")
    def solo_admin(admin: Administrador = Depends(require_admin)):
        ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from core.security import decode_access_token
from models import Usuario, Administrador, Aspirante

# El tokenUrl apunta al endpoint de login que genera el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Dependencia base: extrae y valida el JWT del header `Authorization: Bearer <token>`.
    Retorna el objeto `Usuario` (o subclase) de la BD.
    Lanza HTTP 401 si el token es inválido, expirado o el usuario no existe.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales. Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacta al administrador.",
        )

    return user


def require_aspirante(
    current_user: Usuario = Depends(get_current_user),
) -> Aspirante:
    """
    Variante que además verifica que el usuario sea un Aspirante.
    Lanza HTTP 403 si es un Administrador u otro tipo.
    """
    if not isinstance(current_user, Aspirante):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a aspirantes.",
        )
    return current_user


def require_admin(
    current_user: Usuario = Depends(get_current_user),
) -> Administrador:
    """
    Variante que verifica que el usuario sea un Administrador.
    Lanza HTTP 403 si es un Aspirante u otro tipo.
    """
    if not isinstance(current_user, Administrador):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores.",
        )
    return current_user
