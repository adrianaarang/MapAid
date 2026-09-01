"""Cruce observación-satélite usando imágenes Sentinel-2 en tiempo real.

Cuando alguien reporta algo, este módulo:
1. Busca en Copernicus Data Space las imágenes Sentinel-2 de esa zona
2. Descarga una región pequeña (recorte de ~10km) antes y después
3. Cruza esas imágenes con la descripción de la persona
4. Devuelve: coherente / posible / no_detectable + explicación

Es la versión en tiempo real del cruce: no depende de que haya imágenes
xBD descargadas ni de activaciones previas de Copernicus.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import requests
from PIL import Image

from config import COPERNICUS_PASSWORD, COPERNICUS_USER

# Umbrales calibrados para comparaciones Sentinel-2 reales.
# Sentinel-2 tiene variaciones naturales entre capturas (iluminación,
# ángulo, estación) de hasta un 10-15%. Solo marcamos cambio real
# cuando supera claramente ese ruido de fondo.
_UMBRAL_COHERENTE = 0.30   # cambio claro y significativo
_UMBRAL_POSIBLE   = 0.18   # cambio por encima del ruido de fondo

# Palabras clave por tipo de daño
_KEYWORDS = {
    "derrumbe": ["derrumbe","derrumbado","caído","colapso","destruido","escombros","hundido","derruido"],
    "inundacion": ["agua","inundado","anegado","río","desbordado","barro","lodazal","marea","rotura","tubería"],
    "incendio": ["fuego","incendio","quemado","ceniza","humo","ardiendo","chamuscado"],
    "bloqueo": ["cortado","bloqueado","obstruido","árbol caído","barricada","escombros"],
}

# API de Process de Sentinel Hub (Copernicus Data Space)
_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)

_cache_token: dict = {}


@dataclass
class ResultadoCruce:
    coherencia: str
    puntuacion: float
    categoria: str
    explicacion: str


def _get_token() -> str:
    import time
    ahora = time.time()
    if _cache_token.get("exp", 0) > ahora + 300:
        return _cache_token["tok"]
    r = requests.post(_TOKEN_URL, data={
        "grant_type": "password",
        "client_id": "cdse-public",
        "username": COPERNICUS_USER,
        "password": COPERNICUS_PASSWORD,
    }, timeout=30)
    r.raise_for_status()
    datos = r.json()
    _cache_token["tok"] = datos["access_token"]
    _cache_token["exp"] = ahora + datos.get("expires_in", 600)
    return _cache_token["tok"]


def _descargar_recorte(
    lat: float, lon: float,
    fecha_inicio: str, fecha_fin: str,
) -> Image.Image | None:
    """Descarga el mejor recorte de Sentinel-2 disponible en el rango de fechas."""
    delta = 0.045  # ~5 km
    bbox = [lon - delta, lat - delta, lon + delta, lat + delta]

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{fecha_inicio}T00:00:00Z",
                        "to": f"{fecha_fin}T23:59:59Z",
                    },
                    "maxCloudCoverage": 30,
                    # Mosaico: usa el píxel menos nublado del rango
                    "mosaickingOrder": "leastCC",
                },
            }],
        },
        "output": {
            "width": 256, "height": 256,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": """
            //VERSION=3
            function setup() { return { input: ["B04","B03","B02","CLM"], output: { bands: 3 } }; }
            function evaluatePixel(s) {
                if (s.CLM == 1) return [0.5, 0.5, 0.5]; // nubes → gris
                return [3.5*s.B04, 3.5*s.B03, 3.5*s.B02];
            }
        """,
    }

    try:
        token = _get_token()
        r = requests.post(
            _PROCESS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def _detectar_categoria(texto: str) -> str:
    texto_l = texto.lower()
    for cat, palabras in _KEYWORDS.items():
        if any(p in texto_l for p in palabras):
            return cat
    return "general"


def _puntuacion(img_pre: Image.Image, img_post: Image.Image) -> float:
    a = np.asarray(img_pre,  dtype=np.float32)
    b = np.asarray(img_post, dtype=np.float32)
    dif_brillo  = abs(float(a.mean()) - float(b.mean())) / 255.0
    dif_textura = abs(float(a.std())  - float(b.std()))  / 255.0
    return float(min(1.0, (0.65 * dif_brillo + 0.35 * dif_textura) * 2.2))


def cruzar_con_satelite(
    descripcion: str,
    lat: float,
    lon: float,
    fecha_desastre: str,
    dias_antes: int = 60,
) -> ResultadoCruce:
    """Cruza la descripción con imágenes Sentinel-2 descargadas en tiempo real.

    Args:
        descripcion: texto libre de la persona.
        lat, lon: coordenadas del punto marcado.
        fecha_desastre: YYYY-MM-DD — fecha aproximada del evento.
        dias_antes: días atrás donde buscar la imagen pre.
    """
    from datetime import datetime, timedelta

    categoria = _detectar_categoria(descripcion)

    # Rango PRE: desde (fecha - dias_antes) hasta (fecha - 5 días)
    # Rango POST: desde (fecha) hasta (fecha + 30 días)
    # Así garantizamos que pre y post son capturas distintas
    fecha_dt   = datetime.strptime(fecha_desastre, "%Y-%m-%d")
    pre_inicio = (fecha_dt - timedelta(days=dias_antes)).strftime("%Y-%m-%d")
    pre_fin    = (fecha_dt - timedelta(days=5)).strftime("%Y-%m-%d")
    post_inicio = fecha_desastre
    post_fin   = (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    # Descargar imágenes pre y post usando rangos
    img_pre  = _descargar_recorte(lat, lon, pre_inicio,  pre_fin)
    img_post = _descargar_recorte(lat, lon, post_inicio, post_fin)

    if img_pre is None or img_post is None:
        return ResultadoCruce(
            coherencia="no_detectable",
            puntuacion=0.0,
            categoria=categoria,
            explicacion=(
                "No se pudieron obtener imágenes de Sentinel-2 para esta zona "
                "(puede haber nubes, o la zona no tiene cobertura reciente). "
                "El reporte queda pendiente de validación humana."
            ),
        )

    puntuacion = _puntuacion(img_pre, img_post)

    if puntuacion >= _UMBRAL_COHERENTE:
        coherencia = "coherente"
        explicacion = (
            f"Las imágenes de Sentinel-2 muestran un cambio significativo "
            f"({int(puntuacion*100)}%) en la zona marcada, coherente con "
            f"lo reportado. Pendiente de confirmación humana."
        )
    elif puntuacion >= _UMBRAL_POSIBLE:
        coherencia = "posible"
        explicacion = (
            f"Se detecta un cambio leve ({int(puntuacion*100)}%) en la zona. "
            f"Podría ser coherente con lo reportado, pero no es concluyente. "
            f"Hace falta que una persona confirme in situ."
        )
    else:
        coherencia = "no_detectable"
        explicacion = (
            f"Las imágenes de Sentinel-2 no muestran cambios detectables "
            f"en esta zona ({int(puntuacion*100)}% de variación). "
            f"Esto no significa que el reporte sea falso: muchos daños no "
            f"son visibles desde el satélite. Pendiente de validación humana."
        )

    return ResultadoCruce(
        coherencia=coherencia,
        puntuacion=round(puntuacion, 3),
        categoria=categoria,
        explicacion=explicacion,
    )
