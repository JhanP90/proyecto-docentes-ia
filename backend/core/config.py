# backend/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración centralizada de la aplicación.
    Lee las variables desde el archivo .env ubicado en la raíz del backend.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Base de Datos ---
    # Para desarrollo local con SQLite: sqlite:///./evaluacion_docente.db
    # Para producción con PostgreSQL: postgresql://user:pass@localhost:5432/db_name
    DATABASE_URL: str = "sqlite:///./evaluacion_docente.db"

    # --- Seguridad (JWT) ---
    SECRET_KEY: str = "CAMBIA_ESTE_SECRETO_EN_PRODUCCION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas

    # --- Google Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # --- Almacenamiento de archivos ---
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    # --- CORS ---
    # En producción, reemplaza con la URL real del frontend: ["https://tu-dominio.com"]
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- App ---
    PROJECT_NAME: str = "Sistema de Evaluación Docente - Universidad de Caldas"
    API_V1_STR: str = "/api/v1"


# Instancia global — se importa desde cualquier módulo como:  from core.config import settings
settings = Settings()
