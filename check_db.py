import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.models import HojaDeVida, DatosExtraidosIA

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("--- Hojas de Vida ---")
for hoja in db.query(HojaDeVida).all():
    print(f"ID: {hoja.id}, Estado: {hoja.estado_procesamiento}, Archivo: {hoja.nombre_archivo}")

print("\n--- Datos IA ---")
for dato in db.query(DatosExtraidosIA).all():
    print(f"ID: {dato.id}, Validado: {dato.validado_por_aspirante}")
