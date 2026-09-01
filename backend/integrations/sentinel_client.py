"""Cliente de Copernicus Data Space — imágenes Sentinel-2 en tiempo real.

Dado un punto geográfico y una fecha de desastre, descarga automáticamente:
  - La imagen más reciente SIN nubes ANTES del desastre (pre)
  - La imagen más reciente SIN nubes DESPUÉS del desastre (post)

Usa las mismas credenciales de Copernicus que ya tienes en .env.
No requiere registros adicionales.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from config import COPERNICUS_PASSWORD, COPERNICUS_USER, DATA_RAW_DIR

_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
_CATALOGUE = "https://catalogue.dataspace.copernicus.eu/odata/v1"
_DOWNLOAD  = "https://download.dataspace.copernicus.eu/odata/v1"

_SENTINEL_DIR = Path(DATA_RAW_DIR) / "sentinel"
_TIMEOUT = 60

_cache_token: dict = {}


class SentinelError(Exception):
    """No se pudo obtener la imagen de Sentinel-2."""


# ── Autenticación ─────────────────────────────────────────────────────────

def _token() -> str:
    ahora = time.time()
    if _cache_token.get("exp", 0) > ahora + 300:
        return _cache_token["tok"]

    if not COPERNICUS_USER or not COPERNICUS_PASSWORD:
        raise SentinelError("Faltan COPERNICUS_USER o COPERNICUS_PASSWORD en .env")

    try:
        r = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": "cdse-public",
                "username": COPERNICUS_USER,
                "password": COPERNICUS_PASSWORD,
            },
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise SentinelError(f"Error autenticando en Copernicus: {e}") from e

    datos = r.json()
    _cache_token["tok"] = datos["access_token"]
    _cache_token["exp"] = ahora + datos.get("expires_in", 600)
    return _cache_token["tok"]


def _cabeceras() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


# ── Búsqueda de imágenes ──────────────────────────────────────────────────

def _bbox(lat: float, lon: float, radio_km: float = 5.0) -> tuple:
    """Bounding box alrededor de un punto."""
    delta = radio_km / 111.0
    return (lon - delta, lat - delta, lon + delta, lat + delta)


def _buscar(
    lat: float, lon: float,
    fecha_inicio: str, fecha_fin: str,
    max_nubes: int = 25,
) -> list[dict]:
    """Busca productos Sentinel-2 L2A con pocas nubes en la zona y fechas."""
    oeste, sur, este, norte = _bbox(lat, lon)
    area = f"POLYGON(({oeste} {sur},{este} {sur},{este} {norte},{oeste} {norte},{oeste} {sur}))"

    filtro = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
        f"and att/OData.CSC.DoubleAttribute/Value le {max_nubes}) and "
        f"ContentDate/Start ge {fecha_inicio}T00:00:00.000Z and "
        f"ContentDate/Start le {fecha_fin}T23:59:59.000Z and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{area}')"
    )

    try:
        r = requests.get(
            f"{_CATALOGUE}/Products",
            params={
                "$filter": filtro,
                "$orderby": "ContentDate/Start desc",
                "$top": 5,
                "$expand": "Attributes",
            },
            headers=_cabeceras(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise SentinelError(f"Error buscando imágenes Sentinel-2: {e}") from e

    productos = r.json().get("value", [])
    resultado = []
    for p in productos:
        nubes = next(
            (a["Value"] for a in p.get("Attributes", [])
             if a.get("Name") == "cloudCover"), 100
        )
        resultado.append({
            "id": p["Id"],
            "nombre": p["Name"],
            "fecha": p["ContentDate"]["Start"][:10],
            "nubes": round(nubes, 1),
        })
    return sorted(resultado, key=lambda x: x["nubes"])


def _descargar(producto_id: str, nombre: str) -> Path:
    """Descarga el producto y devuelve la ruta del archivo."""
    _SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
    destino = _SENTINEL_DIR / f"{nombre}.zip"
    if destino.exists():
        return destino

    try:
        with requests.get(
            f"{_DOWNLOAD}/Products({producto_id})/$value",
            headers=_cabeceras(),
            stream=True,
            timeout=300,
        ) as r:
            r.raise_for_status()
            with open(destino, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.RequestException as e:
        if destino.exists():
            destino.unlink()
        raise SentinelError(f"Error descargando imagen: {e}") from e

    return destino


# ── API pública ───────────────────────────────────────────────────────────

def obtener_imagen_zona(
    lat: float,
    lon: float,
    fecha: str,
    momento: str = "post",
    dias_margen: int = 30,
) -> dict:
    """Obtiene la mejor imagen Sentinel-2 de una zona para una fecha.

    Args:
        lat, lon: coordenadas del punto.
        fecha: fecha del desastre (YYYY-MM-DD).
        momento: "pre" (antes) o "post" (después).
        dias_margen: cuántos días buscar antes/después.

    Returns:
        {"id", "nombre", "fecha", "nubes"} del mejor producto encontrado.
    """
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")

    if momento == "pre":
        inicio = (fecha_dt - timedelta(days=dias_margen)).strftime("%Y-%m-%d")
        fin = fecha
    else:
        inicio = fecha
        fin = (fecha_dt + timedelta(days=dias_margen)).strftime("%Y-%m-%d")

    productos = _buscar(lat, lon, inicio, fin)
    if not productos:
        raise SentinelError(
            f"No se encontró imagen Sentinel-2 {momento}-desastre con menos "
            f"del 25% de nubes en un radio de 5 km alrededor de "
            f"({lat:.4f}, {lon:.4f}) entre {inicio} y {fin}."
        )
    return productos[0]


def obtener_par_sentinel(
    lat: float,
    lon: float,
    fecha_desastre: str,
    dias_antes: int = 60,
    dias_despues: int = 30,
) -> dict:
    """Obtiene el par pre/post de imágenes Sentinel-2 más cercanas al desastre.

    Returns:
        {"pre": info_pre, "post": info_post, "bbox": {...}}
    """
    pre  = obtener_imagen_zona(lat, lon, fecha_desastre, "pre",  dias_antes)
    post = obtener_imagen_zona(lat, lon, fecha_desastre, "post", dias_despues)

    oeste, sur, este, norte = _bbox(lat, lon)
    return {
        "pre":  pre,
        "post": post,
        "bbox": {
            "lat_min": sur,  "lon_min": oeste,
            "lat_max": norte, "lon_max": este,
        },
    }
