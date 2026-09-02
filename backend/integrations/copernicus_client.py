"""Cliente de Copernicus Emergency Management Service (CEMS).

Copernicus CEMS es la fuente oficial de imágenes que usa HOT en la vida
real. Cuando ocurre un desastre, publica automáticamente pares de
imágenes antes/después georreferenciadas, accesibles de forma gratuita.

Este cliente hace tres cosas:
  1. Listar activaciones recientes de emergencia (desastres activos).
  2. Descargar el par de imágenes (pre/post) de una activación concreta.
  3. Guardar las imágenes en data/raw/copernicus/ con el mismo formato
     que las de xBD, para que el resto del código las use igual.

Autenticación: OAuth2 con las credenciales de dataspace.copernicus.eu.
Las credenciales van en .env (COPERNICUS_USER y COPERNICUS_PASSWORD),
nunca en el código ni en el repositorio.

Si Copernicus no está disponible (sin red, credenciales incorrectas,
activación sin imágenes aún), se lanza CopernicusError — quien llame
decide si caer de vuelta a xBD o mostrar un aviso al usuario.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from config import (
    COPERNICUS_PASSWORD,
    COPERNICUS_USER,
    DATA_RAW_DIR,
)

# Endpoints oficiales de Copernicus Data Space
_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"
_DOWNLOAD_URL = "https://zipper.dataspace.copernicus.eu/zip"

# Feed público de activaciones CEMS — API JSON (no requiere autenticación).
# OJO: usar la API del portal "mapping" (activations), NO la de "rapidmapping"
# (dashboard-api), que no incluye datos geográficos (centroid) por activación.
_CEMS_API_URL = "https://mapping.emergency.copernicus.eu/activations/api/activations/"

_TIMEOUT = 30
_IMG_DIR = Path(DATA_RAW_DIR) / "copernicus"


class CopernicusError(Exception):
    """No se pudo acceder a Copernicus o la activación no tiene imágenes."""


# ===== AUTENTICACIÓN =====

_token_cache: dict = {}


def _obtener_token() -> str:
    """Token OAuth2, cacheado hasta 5 minutos antes de su expiración."""
    ahora = time.time()
    if _token_cache.get("expira", 0) > ahora + 300:
        return _token_cache["token"]

    if not COPERNICUS_USER or not COPERNICUS_PASSWORD:
        raise CopernicusError(
            "Faltan COPERNICUS_USER o COPERNICUS_PASSWORD en el .env"
        )

    try:
        respuesta = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": "cdse-public",
                "username": COPERNICUS_USER,
                "password": COPERNICUS_PASSWORD,
            },
            timeout=_TIMEOUT,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise CopernicusError(f"No se pudo autenticar en Copernicus: {error}") from error

    datos = respuesta.json()
    _token_cache["token"] = datos["access_token"]
    _token_cache["expira"] = ahora + datos.get("expires_in", 600)
    return _token_cache["token"]


def _cabeceras() -> dict:
    return {"Authorization": f"Bearer {_obtener_token()}"}


# ===== ACTIVACIONES CEMS =====

def _extraer_coordenadas(item: dict) -> tuple[float | None, float | None]:
    """Intenta sacar (lat, lon) de un item de la API CEMS, sea cual sea
    el nombre/formato del campo geográfico que use este endpoint.

    Se prueba en este orden: centroid (WKT o GeoJSON), geometry
    (GeoJSON Point/Polygon), bbox/boundingBox, y campos planos
    lat/lon o latitude/longitude.
    """
    import re

    def _num(v):
        try:
            f = float(v)
            return f if f == f else None  # descarta NaN
        except (TypeError, ValueError):
            return None

    # 1. centroid como WKT: "POINT (lon lat)" o "SRID=4326;POINT (lon lat)"
    centroid = item.get("centroid")
    if isinstance(centroid, str):
        nums = re.findall(r"[-+]?\d*\.?\d+", centroid)
        if len(nums) >= 2:
            lon, lat = _num(nums[-2]), _num(nums[-1])
            if lat is not None and lon is not None:
                return lat, lon

    # 2. centroid o geometry como GeoJSON: {"type": "Point", "coordinates": [lon, lat]}
    for campo in ("centroid", "geometry"):
        geo = item.get(campo)
        if isinstance(geo, dict):
            coords = geo.get("coordinates")
            # Point: [lon, lat]. Polygon/otros: anidado, coger el primer punto.
            while isinstance(coords, list) and coords and isinstance(coords[0], list):
                coords = coords[0]
            if isinstance(coords, list) and len(coords) >= 2:
                lon, lat = _num(coords[0]), _num(coords[1])
                if lat is not None and lon is not None:
                    return lat, lon

    # 3. bounding box: {"west":..,"south":..,"east":..,"north":..} o similares
    for campo in ("bbox", "boundingBox", "bounding_box"):
        bbox = item.get(campo)
        if isinstance(bbox, dict):
            oeste = _num(bbox.get("west", bbox.get("lon_min", bbox.get("minx"))))
            este = _num(bbox.get("east", bbox.get("lon_max", bbox.get("maxx"))))
            sur = _num(bbox.get("south", bbox.get("lat_min", bbox.get("miny"))))
            norte = _num(bbox.get("north", bbox.get("lat_max", bbox.get("maxy"))))
            if None not in (oeste, este, sur, norte):
                return (sur + norte) / 2, (oeste + este) / 2
        elif isinstance(bbox, list) and len(bbox) == 4:
            # formato habitual [oeste, sur, este, norte]
            oeste, sur, este, norte = (_num(v) for v in bbox)
            if None not in (oeste, sur, este, norte):
                return (sur + norte) / 2, (oeste + este) / 2

    # 4. campos planos directos
    lat = _num(item.get("lat", item.get("latitude")))
    lon = _num(item.get("lon", item.get("longitude", item.get("lng"))))
    if lat is not None and lon is not None:
        return lat, lon

    return None, None


def listar_activaciones(max_resultados: int = 10) -> list[dict]:
    """Activaciones recientes de emergencia publicadas por Copernicus CEMS.

    Usa la API JSON pública de Rapid Mapping — no requiere autenticación.
    Devuelve una lista de diccionarios con: codigo, titulo, tipo_desastre,
    fecha, pais, url, latitud, longitud (latitud/longitud pueden ser
    None si la API no trae datos geográficos reconocibles para esa
    activación).
    """
    try:
        respuesta = requests.get(
            _CEMS_API_URL,
            params={"limit": max_resultados, "offset": 0, "ordering": "-activation_time"},
            timeout=_TIMEOUT,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise CopernicusError(f"No se pudo acceder a la API CEMS: {error}") from error

    try:
        datos = respuesta.json()
    except ValueError as error:
        raise CopernicusError("La API CEMS devolvió una respuesta inesperada") from error

    # La API devuelve directamente una lista o un dict con 'results'
    items = datos if isinstance(datos, list) else datos.get("results", datos.get("activations", []))

    if items:
        # Log de depuración: qué claves trae realmente el primer item.
        # Útil una sola vez para confirmar el nombre del campo geográfico
        # de este endpoint concreto; se puede quitar cuando ya no haga falta.
        print(f"[copernicus] Claves disponibles en un item de activación: {sorted(items[0].keys())}")

    activaciones = []
    for item in items[:max_resultados]:
        codigo = item.get("code", item.get("activation_code", ""))
        titulo = item.get("name", item.get("title", item.get("activation_title", "")))
        fecha = (item.get("activationTime", item.get("activation_time", "")) or "")[:10]
        paises = item.get("countries", [])
        pais = ", ".join(p.get("short_name", p) if isinstance(p, dict) else str(p)
                        for p in paises) if paises else ""

        categoria = item.get("category", {})
        tipo = categoria.get("name", categoria.get("slug", "")) if isinstance(categoria, dict) else str(categoria)

        # Traducción básica al español
        traducciones = {
            "flood": "Inundación", "fire": "Incendio", "earthquake": "Terremoto",
            "storm": "Tormenta", "tsunami": "Tsunami", "landslide": "Deslizamiento",
            "volcano": "Volcán", "wildfire": "Incendio forestal", "drought": "Sequía",
        }
        tipo_es = traducciones.get(tipo.lower(), tipo) if tipo else "Emergencia"

        url = f"https://mapping.emergency.copernicus.eu/activations/{codigo}/" if codigo else ""

        lat, lon = _extraer_coordenadas(item)
        if lat is None or lon is None:
            print(f"[copernicus] Activación {codigo} sin coordenadas reconocibles en la API CEMS.")

        activaciones.append({
            "codigo": codigo,
            "titulo": titulo,
            "tipo_desastre": tipo_es,
            "fecha": fecha,
            "pais": pais,
            "url": url,
            "latitud": lat,
            "longitud": lon,
        })

    return activaciones


# ===== IMÁGENES SENTINEL-2 =====

def buscar_imagenes_zona(
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    fecha_inicio: str,
    fecha_fin: str,
    max_nubosidad: int = 20,
) -> list[dict]:
    """Busca imágenes Sentinel-2 L2A de una zona y rango de fechas.

    Devuelve una lista de productos con: id, nombre, fecha, nubosidad,
    tamaño. Se ordenan de menos a más nube.

    Args:
        lat_min/lon_min/lat_max/lon_max: bounding box de la zona.
        fecha_inicio/fecha_fin: formato YYYY-MM-DD.
        max_nubosidad: porcentaje máximo de cobertura de nubes (0-100).
    """
    area = (
        f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},"
        f"{lon_max} {lat_max},{lon_min} {lat_max},{lon_min} {lat_min}))"
    )

    filtros = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
        f"and att/OData.CSC.DoubleAttribute/Value le {max_nubosidad}) and "
        f"ContentDate/Start ge {fecha_inicio}T00:00:00.000Z and "
        f"ContentDate/Start le {fecha_fin}T23:59:59.000Z and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{area}')"
    )

    try:
        respuesta = requests.get(
            f"{_CATALOGUE_URL}/Products",
            params={"$filter": filtros, "$orderby": "ContentDate/Start desc",
                    "$top": 20, "$expand": "Attributes"},
            headers=_cabeceras(),
            timeout=_TIMEOUT,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise CopernicusError(f"Error buscando imágenes: {error}") from error

    productos = respuesta.json().get("value", [])
    resultados = []
    for p in productos:
        nube = next(
            (a["Value"] for a in p.get("Attributes", [])
             if a.get("Name") == "cloudCover"), 100
        )
        resultados.append({
            "id": p["Id"],
            "nombre": p["Name"],
            "fecha": p["ContentDate"]["Start"][:10],
            "nubosidad": round(nube, 1),
            "tamano_mb": round(p.get("ContentLength", 0) / 1024 / 1024, 1),
        })

    return sorted(resultados, key=lambda x: x["nubosidad"])


def descargar_imagen(producto_id: str, nombre_destino: str) -> Path:
    """Descarga un producto Sentinel-2 y lo guarda en data/raw/copernicus/.

    Returns:
        Ruta al archivo descargado.

    Raises:
        CopernicusError: si la descarga falla.
    """
    _IMG_DIR.mkdir(parents=True, exist_ok=True)
    destino = _IMG_DIR / f"{nombre_destino}.zip"

    if destino.exists():
        return destino

    try:
        with requests.get(
            f"{_DOWNLOAD_URL}?productId={producto_id}",
            headers=_cabeceras(),
            stream=True,
            timeout=120,
        ) as respuesta:
            respuesta.raise_for_status()
            with open(destino, "wb") as archivo:
                for chunk in respuesta.iter_content(chunk_size=8192):
                    archivo.write(chunk)
    except requests.RequestException as error:
        raise CopernicusError(f"Error descargando imagen: {error}") from error

    return destino


def obtener_par_imagenes(
    codigo_activacion: str,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    fecha_desastre: str,
    dias_antes: int = 30,
    dias_despues: int = 15,
) -> dict:
    """Obtiene el mejor par de imágenes pre/post para una activación.

    Busca la imagen más reciente sin nubes antes del desastre (pre) y
    la más cercana después (post). Las descarga y devuelve sus rutas.

    Returns:
        {"pre": Path, "post": Path, "escena": str}
    """
    from datetime import datetime, timedelta

    fecha_dt = datetime.strptime(fecha_desastre, "%Y-%m-%d")
    fecha_pre_inicio = (fecha_dt - timedelta(days=dias_antes)).strftime("%Y-%m-%d")
    fecha_pre_fin = fecha_desastre
    fecha_post_inicio = fecha_desastre
    fecha_post_fin = (fecha_dt + timedelta(days=dias_despues)).strftime("%Y-%m-%d")

    # Buscar imagen pre (antes del desastre)
    imgs_pre = buscar_imagenes_zona(
        lat_min, lon_min, lat_max, lon_max, fecha_pre_inicio, fecha_pre_fin
    )
    if not imgs_pre:
        raise CopernicusError(
            f"No se encontró imagen pre-desastre con menos del 20% de nubes "
            f"en los {dias_antes} días anteriores a {fecha_desastre}."
        )

    # Buscar imagen post (después del desastre)
    imgs_post = buscar_imagenes_zona(
        lat_min, lon_min, lat_max, lon_max, fecha_post_inicio, fecha_post_fin
    )
    if not imgs_post:
        raise CopernicusError(
            f"No se encontró imagen post-desastre con menos del 20% de nubes "
            f"en los {dias_despues} días posteriores a {fecha_desastre}."
        )

    escena = f"copernicus-{codigo_activacion}-{fecha_desastre}"
    ruta_pre = descargar_imagen(imgs_pre[0]["id"], f"{escena}_pre")
    ruta_post = descargar_imagen(imgs_post[0]["id"], f"{escena}_post")

    return {
        "escena": escena,
        "pre": ruta_pre,
        "post": ruta_post,
        "info_pre": imgs_pre[0],
        "info_post": imgs_post[0],
    }