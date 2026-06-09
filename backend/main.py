# backend/main.py
"""
Punto de entrada de la aplicación FastAPI.
Aquí se monta el middleware, se registran los routers y se controla
el ciclo de vida de la app (startup/shutdown).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from database import engine, Base, SessionLocal
from models import Usuario, Administrador
from core.security import hash_password
from services.evaluacion_service import inicializar_reglas_por_defecto

# Routers
from api.v1.endpoints import auth, hojas_vida, evaluacion, admin


def _init_db_defaults():
    """Seed the database with a default admin and evaluation rules on first run."""
    db = SessionLocal()
    try:
        inicializar_reglas_por_defecto(db)
        admin_email = "admin@ucaldas.edu.co"
        if not db.query(Usuario).filter(Usuario.email == admin_email).first():
            nuevo_admin = Administrador(
                nombres="Administrador",
                apellidos="Maestro",
                email=admin_email,
                password_hash=hash_password("Admin123*"),
            )
            db.add(nuevo_admin)
            db.commit()
            print(f"Admin por defecto creado: {admin_email}")
    finally:
        db.close()


# ── Ciclo de vida ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta al iniciar el servidor:
      - Crea las tablas si no existen (útil en desarrollo).
      - En producción usa Alembic en su lugar.
    """
    # Aseguramos que el directorio de uploads existe
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Creación de tablas (dev only — en prod usar `alembic upgrade head`)
    Base.metadata.create_all(bind=engine)
    print("Tablas verificadas en la BD")

    _init_db_defaults()

    yield  # La app corre aquí

    # Cleanup al apagar (si se necesita)
    print("Apagando servidor...")


# ── Instancia de la app ──────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST para el Sistema de Evaluación de Aspirantes Docentes",
    version="1.0.0",
    docs_url="/api/docs",       # Swagger UI
    redoc_url="/api/redoc",     # ReDoc
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Archivos estáticos (carpeta uploads) ─────────────────────────
# Los PDFs subidos se servirán como:  GET /uploads/nombre_archivo.pdf
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Routers ──────────────────────────────────────────────────────
app.include_router(auth.router,        prefix=settings.API_V1_STR + "/auth",        tags=["Auth"])
app.include_router(hojas_vida.router,  prefix=settings.API_V1_STR + "/hojas-vida",  tags=["Hojas de Vida"])
app.include_router(evaluacion.router,  prefix=settings.API_V1_STR + "/evaluacion",  tags=["Evaluación"])
app.include_router(admin.router,       prefix=settings.API_V1_STR + "/admin",       tags=["Admin"])

# Próximas capas (se activarán iterativamente):
# from api.v1.endpoints import aspirantes, hojas_vida, evaluacion, admin
# app.include_router(aspirantes.router, prefix=settings.API_V1_STR + "/aspirantes", tags=["Aspirantes"])
# app.include_router(hojas_vida.router, prefix=settings.API_V1_STR + "/hojas-vida", tags=["HojaDeVida"])
# app.include_router(evaluacion.router, prefix=settings.API_V1_STR + "/evaluacion", tags=["Evaluación"])
# app.include_router(admin.router,      prefix=settings.API_V1_STR + "/admin",      tags=["Admin"])


# ── Health check ─────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/api/docs",
    }