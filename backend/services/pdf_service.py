# backend/services/pdf_service.py
"""
Servicio de extracción de texto desde archivos PDF.

Usa `pdfplumber` como motor principal. Diseñado para ser llamado
desde el servicio de IA, que luego envía el texto a Gemini.

Principios:
  - Extrae texto página por página y lo une con separadores claros.
  - Detecta PDFs de solo imagen (texto vacío → flag `es_solo_imagen`).
  - No hace parsing semántico — eso es trabajo de Gemini.
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ResultadoExtraccionPDF:
    texto: str            # Texto completo extraído
    paginas: int          # Número de páginas
    es_solo_imagen: bool  # True si no se pudo extraer texto (PDF escaneado)
    advertencias: list[str]


def extraer_texto_pdf(ruta_archivo: str) -> ResultadoExtraccionPDF:
    """
    Extrae todo el texto de un PDF usando pdfplumber.

    Args:
        ruta_archivo: Ruta absoluta al archivo PDF.

    Returns:
        ResultadoExtraccionPDF con el texto, metadata y advertencias.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el archivo no es un PDF válido o está protegido con contraseña.
    """
    ruta = Path(ruta_archivo)

    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")

    if ruta.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo no es un PDF: {ruta.suffix}")

    advertencias: list[str] = []
    bloques_texto: list[str] = []
    total_paginas = 0

    try:
        with pdfplumber.open(ruta) as pdf:
            total_paginas = len(pdf.pages)

            if total_paginas == 0:
                raise ValueError("El PDF no contiene páginas.")

            for i, pagina in enumerate(pdf.pages, start=1):
                try:
                    texto_pagina = pagina.extract_text()

                    if texto_pagina and texto_pagina.strip():
                        # Agregamos un encabezado de página para que la IA
                        # pueda contextualizar mejor secciones del CV
                        bloques_texto.append(
                            f"--- PAGINA {i} ---\n{texto_pagina.strip()}"
                        )
                    else:
                        advertencias.append(
                            f"Página {i}: sin texto extraíble (posiblemente imagen)."
                        )

                except Exception as e:
                    advertencias.append(f"Página {i}: error al extraer ({e}).")
                    logger.warning("Error extrayendo página %d de %s: %s", i, ruta_archivo, e)

    except pdfplumber.pdfminer.pdfpage.PDFPasswordIncorrect:
        raise ValueError(
            "El PDF está protegido con contraseña. Por favor, sube una versión sin restricciones."
        )
    except Exception as e:
        logger.error("Error abriendo PDF %s: %s", ruta_archivo, e)
        raise ValueError(f"No se pudo procesar el PDF: {e}")

    texto_completo = "\n\n".join(bloques_texto)
    es_solo_imagen = len(texto_completo.strip()) == 0

    if es_solo_imagen:
        advertencias.append(
            "El PDF parece ser un documento escaneado sin texto seleccionable. "
            "La extracción con IA puede tener baja precisión."
        )

    logger.info(
        "PDF procesado: %s | %d páginas | %d caracteres extraídos | solo_imagen=%s",
        ruta.name, total_paginas, len(texto_completo), es_solo_imagen
    )

    return ResultadoExtraccionPDF(
        texto=texto_completo,
        paginas=total_paginas,
        es_solo_imagen=es_solo_imagen,
        advertencias=advertencias,
    )
