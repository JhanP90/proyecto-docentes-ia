import uuid
# backend/services/evaluacion_service.py
"""
Motor de Reglas Dinámico para la Evaluación de Aspirantes.

Este servicio toma los datos estructurados extraídos por la IA (idealmente 
ya validados por el aspirante) y aplica las reglas de puntuación almacenadas 
en la base de datos (tabla `reglas_evaluacion`).

Reglas de negocio:
1. Cada ítem (ej. DOCTORADO, DOCENCIA_UNIVERSITARIA) suma un puntaje base.
2. Si la regla tiene `unidad` = "AÑO", se multiplica el puntaje por la duración.
3. Cada categoría (ej. FORMACION, EXPERIENCIA) tiene un tope máximo.
4. El puntaje total es la suma de los puntajes por categoría tras aplicar los topes.
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from models import (
    ResultadoEvaluacion, DatosExtraidosIA, ReglaEvaluacion, CategoriaRegla, Aspirante
)
from schemas import DatosExtraidosGemini

logger = logging.getLogger(__name__)


def calcular_puntaje_aspirante(db: Session, aspirante_id: str) -> ResultadoEvaluacion:
    """
    Calcula (o recalcula) el puntaje total de un aspirante basado en sus datos de IA
    y las reglas de evaluación vigentes en la BD.

    Args:
        db: Sesión de SQLAlchemy.
        aspirante_id: ID del aspirante.

    Returns:
        ResultadoEvaluacion: El registro guardado con el desglose del puntaje.

    Raises:
        ValueError: Si el aspirante no tiene datos extraídos listos para evaluar.
    """
    # 1. Obtener los datos de IA del aspirante
    # Buscamos a través de la relación aspirante -> hoja_vida -> datos_extraidos
    aspirante = db.query(Aspirante).filter(Aspirante.id == (uuid.UUID(aspirante_id) if isinstance(aspirante_id, str) else aspirante_id)).first()
    if not aspirante:
        raise ValueError(f"Aspirante {aspirante_id} no encontrado.")

    if not aspirante.hoja_vida or not aspirante.hoja_vida.datos_extraidos:
        raise ValueError("El aspirante no tiene una hoja de vida procesada por IA.")

    registro_ia: DatosExtraidosIA = aspirante.hoja_vida.datos_extraidos

    # Usamos los datos validados por el aspirante si existen, si no, usamos los crudos de la IA.
    # En un flujo estricto, podríamos exigir que `validado_por_aspirante` sea True.
    json_data = registro_ia.json_validado if registro_ia.json_validado else registro_ia.json_estructurado
    datos_cv = DatosExtraidosGemini.model_validate(json_data)

    # 2. Cargar todas las reglas activas de la BD
    reglas_db = db.query(ReglaEvaluacion).filter(ReglaEvaluacion.activo == True).all()
    
    # Organizar reglas en un diccionario para acceso rápido: dict[categoria][nombre_item] = regla
    mapa_reglas: dict[CategoriaRegla, dict[str, ReglaEvaluacion]] = {cat: {} for cat in CategoriaRegla}
    topes_categoria: dict[CategoriaRegla, float] = {}

    for regla in reglas_db:
        # Normalizar el nombre del item a mayúsculas para hacer match exacto
        item_normalizado = regla.nombre_item.strip().upper()
        mapa_reglas[regla.categoria][item_normalizado] = regla
        # Asumimos que el tope es el mismo para todos los items de una categoría
        topes_categoria[regla.categoria] = regla.tope_maximo_categoria

    # 3. Calcular puntajes por categoría (sin topes aún)
    puntajes_crudos: dict[CategoriaRegla, float] = {cat: 0.0 for cat in CategoriaRegla}

    # -- A. FORMACION (Títulos Académicos)
    for titulo in datos_cv.titulos_academicos:
        nivel = titulo.nivel.upper()
        regla = mapa_reglas[CategoriaRegla.FORMACION].get(nivel)
        if regla:
            puntajes_crudos[CategoriaRegla.FORMACION] += regla.puntos_por_item
            logger.debug("Sumando %f puntos por FORMACION: %s", regla.puntos_por_item, nivel)

    # -- B. EXPERIENCIA (Experiencia Laboral)
    for exp in datos_cv.experiencia_laboral:
        tipo = exp.tipo.upper()
        regla = mapa_reglas[CategoriaRegla.EXPERIENCIA].get(tipo)
        if regla and exp.años_calculados is not None and exp.años_calculados > 0:
            # Multiplicamos los puntos base por la cantidad de años si la unidad lo indica, 
            # o si lógicamente la experiencia se mide en años.
            puntos_exp = regla.puntos_por_item * exp.años_calculados
            puntajes_crudos[CategoriaRegla.EXPERIENCIA] += puntos_exp
            logger.debug("Sumando %f puntos por EXPERIENCIA (%s, %f años)", puntos_exp, tipo, exp.años_calculados)

    # -- C. PRODUCCION (Publicaciones)
    for pub in datos_cv.publicaciones:
        tipo = pub.tipo.upper()
        regla = mapa_reglas[CategoriaRegla.PRODUCCION].get(tipo)
        if regla:
            puntajes_crudos[CategoriaRegla.PRODUCCION] += regla.puntos_por_item
            logger.debug("Sumando %f puntos por PRODUCCION: %s", regla.puntos_por_item, tipo)

    # -- D. PONENCIAS
    for pon in datos_cv.ponencias:
        tipo = pon.tipo.upper()
        regla = mapa_reglas[CategoriaRegla.PONENCIAS].get(tipo)
        if regla:
            puntajes_crudos[CategoriaRegla.PONENCIAS] += regla.puntos_por_item
            logger.debug("Sumando %f puntos por PONENCIAS: %s", regla.puntos_por_item, tipo)

    # -- E. INVESTIGACION (Proyectos)
    for proy in datos_cv.proyectos_investigacion:
        rol = proy.rol.upper()
        regla = mapa_reglas[CategoriaRegla.INVESTIGACION].get(rol)
        if regla:
            puntajes_crudos[CategoriaRegla.INVESTIGACION] += regla.puntos_por_item
            logger.debug("Sumando %f puntos por INVESTIGACION: %s", regla.puntos_por_item, rol)


    # 4. Aplicar topes por categoría y calcular total
    desglose_final: dict[str, float] = {}
    puntaje_total = 0.0

    for cat in CategoriaRegla:
        crudo = puntajes_crudos[cat]
        tope = topes_categoria.get(cat, float('inf'))  # Si no hay regla que defina tope, asumimos infinito (o 0, dependiendo de la política)
        
        # Si no había reglas en la BD para esta categoría, el tope quedará como inf. 
        # Es mejor si forzamos a 0 si no hay reglas.
        if cat not in topes_categoria and crudo == 0:
            tope = 0.0

        puntaje_aplicado = min(crudo, tope)
        desglose_final[cat.value] = puntaje_aplicado
        puntaje_total += puntaje_aplicado
        
        logger.debug("Categoria %s: Crudo=%f, Tope=%f -> Aplicado=%f", cat.value, crudo, tope, puntaje_aplicado)

    # 5. Guardar o actualizar en la BD
    resultado_existente = db.query(ResultadoEvaluacion).filter(
        ResultadoEvaluacion.aspirante_id == aspirante_id
    ).first()

    if resultado_existente:
        resultado_existente.puntaje_total = puntaje_total
        resultado_existente.desglose_puntaje = desglose_final
        resultado_existente.recalculado = True
        # La fecha de cálculo se actualiza automáticamente con onupdate (si estuviera configurado)
        # pero forzaremos una actualización de ser necesario.
        db.commit()
        db.refresh(resultado_existente)
        logger.info("Resultado de evaluacion ACTUALIZADO para aspirante %s. Total: %f", aspirante_id, puntaje_total)
        return resultado_existente
    else:
        nuevo_resultado = ResultadoEvaluacion(
            aspirante_id=aspirante_id,
            puntaje_total=puntaje_total,
            desglose_puntaje=desglose_final,
            recalculado=False
        )
        db.add(nuevo_resultado)
        db.commit()
        db.refresh(nuevo_resultado)
        logger.info("Resultado de evaluacion CREADO para aspirante %s. Total: %f", aspirante_id, puntaje_total)
        return nuevo_resultado


def inicializar_reglas_por_defecto(db: Session):
    """
    Utilidad para poblar la tabla de Reglas de Evaluación con los valores
    base si la tabla está vacía.
    """
    if db.query(ReglaEvaluacion).first() is not None:
        return # Ya hay reglas

    reglas_base = [
        # Formación (Tope: 40)
        ReglaEvaluacion(categoria=CategoriaRegla.FORMACION, nombre_item="DOCTORADO", puntos_por_item=40.0, tope_maximo_categoria=40.0),
        ReglaEvaluacion(categoria=CategoriaRegla.FORMACION, nombre_item="MAESTRIA", puntos_por_item=20.0, tope_maximo_categoria=40.0),
        ReglaEvaluacion(categoria=CategoriaRegla.FORMACION, nombre_item="ESPECIALIZACION", puntos_por_item=10.0, tope_maximo_categoria=40.0),
        ReglaEvaluacion(categoria=CategoriaRegla.FORMACION, nombre_item="PREGRADO", puntos_por_item=5.0, tope_maximo_categoria=40.0),
        
        # Experiencia (Tope: 20)
        ReglaEvaluacion(categoria=CategoriaRegla.EXPERIENCIA, nombre_item="DOCENCIA_UNIVERSITARIA", puntos_por_item=2.0, tope_maximo_categoria=20.0, unidad="AÑO"),
        ReglaEvaluacion(categoria=CategoriaRegla.EXPERIENCIA, nombre_item="INVESTIGACION", puntos_por_item=2.0, tope_maximo_categoria=20.0, unidad="AÑO"),
        ReglaEvaluacion(categoria=CategoriaRegla.EXPERIENCIA, nombre_item="PROFESIONAL", puntos_por_item=1.0, tope_maximo_categoria=20.0, unidad="AÑO"),
        
        # Producción (Tope: 50)
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="ARTICULO_A1", puntos_por_item=15.0, tope_maximo_categoria=50.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="ARTICULO_A2", puntos_por_item=12.0, tope_maximo_categoria=50.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="ARTICULO_B", puntos_por_item=8.0, tope_maximo_categoria=50.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="ARTICULO_C", puntos_por_item=5.0, tope_maximo_categoria=50.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="LIBRO", puntos_por_item=20.0, tope_maximo_categoria=50.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PRODUCCION, nombre_item="CAPITULO_LIBRO", puntos_por_item=10.0, tope_maximo_categoria=50.0),
        
        # Ponencias (Tope: 10)
        ReglaEvaluacion(categoria=CategoriaRegla.PONENCIAS, nombre_item="PONENCIA_INTERNACIONAL", puntos_por_item=3.0, tope_maximo_categoria=10.0),
        ReglaEvaluacion(categoria=CategoriaRegla.PONENCIAS, nombre_item="PONENCIA_NACIONAL", puntos_por_item=1.0, tope_maximo_categoria=10.0),
        
        # Investigación (Tope: 20)
        ReglaEvaluacion(categoria=CategoriaRegla.INVESTIGACION, nombre_item="INVESTIGADOR_PRINCIPAL", puntos_por_item=5.0, tope_maximo_categoria=20.0),
        ReglaEvaluacion(categoria=CategoriaRegla.INVESTIGACION, nombre_item="CO_INVESTIGADOR", puntos_por_item=2.0, tope_maximo_categoria=20.0),
    ]

    db.add_all(reglas_base)
    db.commit()
    logger.info("Reglas base de evaluación inicializadas en la BD.")
