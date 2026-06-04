# backend/core/security.py
"""
Utilidades de seguridad puras (sin dependencias de FastAPI).
  - Hash y verificación de passwords con bcrypt.
  - Generación y decodificación de JWT con python-jose.

Este módulo NO importa FastAPI a propósito, para poder ser testeado
de forma aislada sin levantar la app.
"""
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

# passlib 1.7.4 intenta leer bcrypt.__about__ que fue removido en bcrypt>=4.x.
# El warning es inofensivo — hash y verify funcionan correctamente.
warnings.filterwarnings("ignore", ".*error reading bcrypt version.*")

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

# ── Contexto de hashing ──────────────────────────────────────────
# bcrypt con cost-factor por defecto (12) — buen equilibrio seguridad/velocidad
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Retorna el hash bcrypt del password en texto plano."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara el password en texto plano contra el hash almacenado.
    Retorna True si coinciden, False en caso contrario.
    Usa comparación en tiempo constante para evitar timing attacks.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT ──────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    tipo_usuario: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Genera un JWT firmado con HS256.

    Args:
        subject:      El identificador único del usuario (UUID como string).
        tipo_usuario: "aspirante" | "admin" — se incluye en el payload.
        expires_delta: Tiempo de expiración personalizado. Si es None, usa
                       ACCESS_TOKEN_EXPIRE_MINUTES del config.

    Returns:
        Token JWT firmado como string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,           # subject — identificador del usuario
        "tipo": tipo_usuario,     # claim propio: rol del usuario
        "exp": expire,            # expiración estándar JWT
        "iat": datetime.now(timezone.utc),  # issued at
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT.

    Returns:
        El payload dict si el token es válido y no expiró.
        None si el token es inválido, expiró o fue manipulado.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
