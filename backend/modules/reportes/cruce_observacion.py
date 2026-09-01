"""Pieza 2 de la IA de MapAid — cruce observación-satélite.

Recibe la descripción libre de una persona y las imágenes de satélite
de la zona que señaló, y responde si lo que describe es coherente con
lo que se ve desde arriba.

Respuestas posibles
-------------------
- coherente      : el satélite ve un cambio significativo donde la persona
                   dice que hay daño/agua/fuego. Refuerza el reporte.
- posible        : hay algo diferente en la imagen pero no es concluyente.
                   Puede ser verdad, hace falta confirmación humana.
- no_detectable  : la imagen no permite saberlo (daño interno, zona bajo
                   nubes, resolución insuficiente). No quiere decir que
                   la persona mienta.

Por qué este enfoque y no un LLM
---------------------------------
Un LLM podría "alucinar" coherencia: si el texto dice "hay agua" y el
modelo quiere ser útil, podría confirmar aunque la imagen no lo muestre.
Este módulo es determinista: cruza señales visuales medibles con
palabras clave del texto. Lo que devuelve tiene una explicación basada
en datos reales, no en probabilidades de lenguaje.

Qué NO hace
-----------
- No interpreta texto ambiguo ("algo raro", "parece que...")
- No detecta daño estructural interno
- Se confunde con sombras, nubes y cambios de ángulo de captura
Todo esto se declara en la respuesta para que quien valida lo sepa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from modules.deteccion.comparador import (
    _puntuacion_de_cambio,
    polygon_bbox,
)

# Radio en píxeles alrededor del punto marcado que se recorta para analizar.
# A la resolución de Sentinel-2 (10m/px), 50px ≈ 500m de radio.
_RADIO_PX = 50

# Umbrales de cambio visual para la clasificación
_UMBRAL_COHERENTE = 0.18   # cambio claro
_UMBRAL_POSIBLE   = 0.08   # cambio leve

# Palabras clave por categoría de daño y sus señales visuales esperadas
_KEYWORDS = {
    "derrumbe": ["derrumbe", "derrumbado", "caído", "caida", "colapso", "colapsado",
                 "destruido", "escombros", "ruinas", "hundido"],
    "inundacion": ["agua", "inundado", "inundación", "anegado", "anegada", "río",
                   "desbordado", "barro", "lodazal", "marea"],
    "incendio": ["fuego", "incendio", "quemado", "quemada", "ceniza", "humo",
                 "chamuscado", "ardiendo"],
    "bloqueo": ["cortado", "cortada", "bloqueado", "bloqueada", "obstruido",
                "barricada", "escombros", "árbol caído"],
}


@dataclass
class ResultadoCruce:
    """Resultado del cruce observación-satélite."""

    coherencia: str          # "coherente" | "posible" | "no_detectable"
    puntuacion_cambio: float # 0-1: cuánto cambió la zona en la imagen
    categoria_detectada: str # qué tipo de daño detectó el texto
    explicacion: str         # texto legible para mostrar en la interfaz


def _detectar_categoria(texto: str) -> str:
    """Qué tipo de daño menciona el texto."""
    texto_lower = texto.lower()
    for categoria, palabras in _KEYWORDS.items():
        if any(p in texto_lower for p in palabras):
            return categoria
    return "general"


def _recortar_zona(
    imagen: Image.Image,
    lat_punto: float,
    lon_punto: float,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
) -> np.ndarray | None:
    """Recorta la zona alrededor del punto en coordenadas de píxel.

    Convierte las coordenadas geográficas a píxeles asumiendo que la
    imagen cubre el bounding box lat_min/lon_min → lat_max/lon_max de
    forma lineal (proyección simple, suficiente para imágenes de zona).
    """
    ancho, alto = imagen.size
    if lat_max == lat_min or lon_max == lon_min:
        return None

    px = int((lon_punto - lon_min) / (lon_max - lon_min) * ancho)
    py = int((lat_max - lat_punto) / (lat_max - lat_min) * alto)  # lat invertida

    izq = max(0, px - _RADIO_PX)
    arr = max(0, py - _RADIO_PX)
    der = min(ancho, px + _RADIO_PX)
    aba = min(alto, py + _RADIO_PX)

    if der - izq < 4 or aba - arr < 4:
        return None

    return np.asarray(imagen.crop((izq, arr, der, aba)).convert("L"), dtype=np.float32)


def cruzar_observacion(
    descripcion: str,
    lat_punto: float,
    lon_punto: float,
    ruta_pre: str | Path,
    ruta_post: str | Path,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
) -> ResultadoCruce:
    """Cruza la descripción de una persona con las imágenes de satélite.

    Args:
        descripcion: texto libre de la persona.
        lat_punto/lon_punto: coordenadas del punto marcado en el mapa.
        ruta_pre/ruta_post: rutas a las imágenes de satélite antes/después.
        lat_min/lon_min/lat_max/lon_max: bounding box de las imágenes.

    Returns:
        ResultadoCruce con la coherencia, la puntuación de cambio y
        una explicación legible.
    """
    categoria = _detectar_categoria(descripcion)

    # Intentar cargar las imágenes — puede fallar si no están descargadas
    try:
        img_pre = Image.open(ruta_pre).convert("RGB")
        img_post = Image.open(ruta_post).convert("RGB")
    except (OSError, FileNotFoundError):
        return ResultadoCruce(
            coherencia="no_detectable",
            puntuacion_cambio=0.0,
            categoria_detectada=categoria,
            explicacion=(
                "No se pudieron cargar las imágenes de satélite de esta zona. "
                "El reporte queda pendiente de validación humana."
            ),
        )

    # Recortar la zona alrededor del punto marcado
    recorte_pre = _recortar_zona(img_pre, lat_punto, lon_punto,
                                  lat_min, lon_min, lat_max, lon_max)
    recorte_post = _recortar_zona(img_post, lat_punto, lon_punto,
                                   lat_min, lon_min, lat_max, lon_max)

    if recorte_pre is None or recorte_post is None:
        return ResultadoCruce(
            coherencia="no_detectable",
            puntuacion_cambio=0.0,
            categoria_detectada=categoria,
            explicacion=(
                "El punto marcado está fuera del área cubierta por las "
                "imágenes de satélite disponibles."
            ),
        )

    # Medir el cambio visual en la zona
    puntuacion = _puntuacion_de_cambio(recorte_pre, recorte_post)

    # Clasificar
    if puntuacion >= _UMBRAL_COHERENTE:
        coherencia = "coherente"
        explicacion = _explicacion_coherente(categoria, puntuacion)
    elif puntuacion >= _UMBRAL_POSIBLE:
        coherencia = "posible"
        explicacion = _explicacion_posible(categoria, puntuacion)
    else:
        coherencia = "no_detectable"
        explicacion = _explicacion_no_detectable(categoria)

    return ResultadoCruce(
        coherencia=coherencia,
        puntuacion_cambio=round(puntuacion, 3),
        categoria_detectada=categoria,
        explicacion=explicacion,
    )


def _explicacion_coherente(categoria: str, puntuacion: float) -> str:
    pct = int(puntuacion * 100)
    base = {
        "derrumbe": f"La imagen de satélite muestra un cambio significativo ({pct}%) en la zona marcada, coherente con un posible derrumbe o daño estructural.",
        "inundacion": f"Se detecta un cambio importante ({pct}%) en la zona, consistente con presencia de agua o barro.",
        "incendio": f"Cambio visual significativo ({pct}%) en la zona, coherente con posibles efectos de incendio.",
        "bloqueo": f"La imagen muestra cambios ({pct}%) en el área de la vía señalada.",
        "general": f"La imagen de satélite confirma un cambio significativo ({pct}%) en la zona marcada.",
    }
    return base.get(categoria, base["general"]) + " Pendiente de confirmación humana."


def _explicacion_posible(categoria: str, puntuacion: float) -> str:
    pct = int(puntuacion * 100)
    return (
        f"Se detecta un cambio leve ({pct}%) en la zona marcada. "
        f"Podría ser coherente con lo reportado, pero no es concluyente. "
        f"Hace falta que una persona confirme in situ."
    )


def _explicacion_no_detectable(categoria: str) -> str:
    razones = {
        "derrumbe": "El satélite no detecta cambios visibles desde arriba (posible daño interno, tejado intacto).",
        "inundacion": "No se detecta agua desde el satélite en esta zona (puede haber nubes o la inundación puede haber remitido).",
        "incendio": "No se detectan cambios de color o textura coherentes con un incendio en esta zona.",
        "bloqueo": "No se detectan cambios en la vía desde el satélite (un árbol caído puede no ser visible a esta resolución).",
        "general": "La imagen de satélite no muestra cambios detectables en esta zona.",
    }
    return (
        razones.get(categoria, razones["general"]) +
        " Esto no significa que el reporte sea falso: muchos daños no son "
        "visibles desde el satélite. Pendiente de validación humana."
    )
