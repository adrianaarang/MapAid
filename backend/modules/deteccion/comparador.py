"""Comparación de imágenes antes/después — la parte de IA de MapAid.

Qué hace
--------
Para cada edificio ya delimitado en el mapa base (el polígono viene de
las etiquetas de xBD, que hacen aquí el papel del mapa de OpenStreetMap
previo al desastre), recorta esa misma región en la imagen de antes y en
la de después, y mide cuánto ha cambiado. A partir de esa diferencia
estima un nivel de daño y una confianza.

Por qué así y no una red neuronal
---------------------------------
Es un método clásico de visión por computador (diferencia de intensidad
y de textura entre dos recortes registrados), no un modelo entrenado. Se
eligió a propósito: es explicable, determinista y no necesita GPU ni
horas de entrenamiento, lo que encaja con el plazo del reto. El objetivo
de MapAid no es ganar en precisión a un modelo de xView2, sino demostrar
un flujo donde la IA propone y una persona valida.

Qué NO detecta (importante decirlo en la demo)
----------------------------------------------
- Daño estructural interno con el techo intacto: desde arriba se ve igual.
- Cambios que no alteran el brillo/textura del tejado.
- Se confunde con sombras, nubes y con imágenes tomadas a distinto
  ángulo o a distinta hora del día: puede marcar cambio donde no lo hay.

Por eso ninguna salida de este módulo se considera verdad: todas nacen
como "pendiente" y necesitan validación humana.
"""
from __future__ import annotations

import math
import re

import numpy as np
from PIL import Image

from modules.deteccion.schemas import DamageLevel

# Umbrales de diferencia (0-1) para pasar de una puntuación continua a la
# escala discreta de xBD. Ajustables: son el principal punto de calibración
# del sistema, y conviene revisarlos si se cambia de tipo de desastre.
_THRESHOLD_MINOR = 0.12
_THRESHOLD_MAJOR = 0.22
_THRESHOLD_DESTROYED = 0.34


def parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    """Extrae los vértices de un POLYGON en formato WKT.

    Las etiquetas de xBD guardan la geometría como texto WKT, tanto en
    píxeles ("xy") como en coordenadas geográficas ("lng_lat").
    """
    numeros = re.findall(r"(-?\d+\.?\d*(?:[eE][-+]?\d+)?)", wkt)
    valores = [float(n) for n in numeros]
    return list(zip(valores[0::2], valores[1::2]))


def polygon_centroid(puntos: list[tuple[float, float]]) -> tuple[float, float]:
    """Centro medio de un polígono (suficiente para colocar un marcador)."""

    if not puntos:
        return (0.0, 0.0)
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def polygon_bbox(
    puntos: list[tuple[float, float]], ancho: int, alto: int
) -> tuple[int, int, int, int] | None:
    """Caja que encierra al polígono, recortada a los límites de la imagen."""

    if not puntos:
        return None

    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]

    izq = max(0, int(math.floor(min(xs))))
    arr = max(0, int(math.floor(min(ys))))
    der = min(ancho, int(math.ceil(max(xs))))
    aba = min(alto, int(math.ceil(max(ys))))

    if der - izq < 2 or aba - arr < 2:
        return None
    return (izq, arr, der, aba)


def _puntuacion_de_cambio(antes: np.ndarray, despues: np.ndarray) -> float:
    """Cuánto ha cambiado un recorte, de 0 (nada) a 1 (irreconocible).

    Combina dos señales que se complementan:

    - Diferencia de brillo medio: capta que un tejado pase a ser escombro
      claro, o que una zona quede cubierta de agua o ceniza.
    - Diferencia de textura (desviación típica): capta que una superficie
      lisa (un tejado entero) pase a ser irregular (escombros), aunque el
      brillo medio se mantenga parecido.

    Se normaliza a 0-1 dividiendo por el rango máximo posible (255).
    """
    if antes.size == 0 or despues.size == 0:
        return 0.0

    dif_brillo = abs(float(antes.mean()) - float(despues.mean())) / 255.0
    dif_textura = abs(float(antes.std()) - float(despues.std())) / 255.0

    # El brillo pesa más porque es la señal más estable entre capturas;
    # la textura afina los casos en que el color apenas cambia.
    puntuacion = 0.65 * dif_brillo + 0.35 * dif_textura

    # Escalado empírico: las diferencias reales rara vez superan 0.4, así
    # que se estira el rango útil para que los umbrales sean legibles.
    return float(min(1.0, puntuacion * 2.2))


def _nivel_de_dano(puntuacion: float) -> DamageLevel:
    """Traduce la puntuación continua a la escala discreta de xBD."""

    if puntuacion >= _THRESHOLD_DESTROYED:
        return DamageLevel.DESTROYED
    if puntuacion >= _THRESHOLD_MAJOR:
        return DamageLevel.MAJOR
    if puntuacion >= _THRESHOLD_MINOR:
        return DamageLevel.MINOR
    return DamageLevel.NO_DAMAGE


def comparar_edificio(
    img_antes: Image.Image,
    img_despues: Image.Image,
    poligono_px: list[tuple[float, float]],
) -> tuple[DamageLevel, float]:
    """Compara un edificio entre las dos imágenes.

    Si el modelo entrenado (modelo_danos.pt) está disponible, lo usa.
    Si no, usa el comparador clásico de brillo/textura.
    """
    ancho, alto = img_antes.size
    caja = polygon_bbox(poligono_px, ancho, alto)
    if caja is None:
        return (DamageLevel.UNCLASSIFIED, 0.0)

    # Intentar primero con el modelo neuronal entrenado
    try:
        from ia.modelo import inferir_edificio
        resultado = inferir_edificio(img_antes, img_despues, caja)
        if resultado is not None:
            return resultado
    except ImportError:
        pass

    # Fallback: comparador clásico de píxeles
    gris_antes = np.asarray(img_antes.crop(caja).convert("L"), dtype=np.float32)
    gris_despues = np.asarray(img_despues.crop(caja).convert("L"), dtype=np.float32)

    puntuacion = _puntuacion_de_cambio(gris_antes, gris_despues)
    nivel = _nivel_de_dano(puntuacion)

    distancia_frontera = min(
        abs(puntuacion - _THRESHOLD_MINOR),
        abs(puntuacion - _THRESHOLD_MAJOR),
        abs(puntuacion - _THRESHOLD_DESTROYED),
    )
    confianza = 0.35 + min(0.57, distancia_frontera * 4.0)

    return (nivel, round(confianza, 2))
