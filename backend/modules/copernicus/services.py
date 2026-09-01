"""Servicio que conecta una activación Copernicus con el flujo de análisis.

Este es el puente que faltaba:
  Activación Copernicus → descargar imágenes → nueva escena → analizar con la IA

Cuando una administradora pulsa "Usar esta activación", este servicio:
1. Busca las imágenes pre/post en el catálogo de Copernicus para la zona
   y fecha de la activación.
2. Las descarga en data/raw/copernicus/.
3. Crea una "escena" con el mismo formato que xBD para que el comparador
   la procese sin cambios.
4. Devuelve el nombre de la escena lista para analizar.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import DATA_RAW_DIR
from integrations.copernicus_client import CopernicusError, obtener_par_imagenes

_COPERNICUS_DIR = Path(DATA_RAW_DIR) / "copernicus"
_METADATA_FILE = _COPERNICUS_DIR / "escenas.json"


def escenas_copernicus() -> list[dict]:
    """Lista las escenas descargadas de Copernicus disponibles para analizar."""
    if not _METADATA_FILE.exists():
        return []
    try:
        return json.loads(_METADATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _guardar_metadata(escenas: list[dict]) -> None:
    _COPERNICUS_DIR.mkdir(parents=True, exist_ok=True)
    _METADATA_FILE.write_text(
        json.dumps(escenas, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def descargar_escena_activacion(
    codigo: str,
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    fecha_desastre: str,
    titulo: str = "",
    tipo_desastre: str = "",
    dias_antes: int = 30,
    dias_despues: int = 15,
) -> dict:
    """Descarga las imágenes de una activación y la registra como escena.

    Devuelve los datos de la escena creada, lista para pasar a
    /api/deteccion/analizar.

    Si la escena ya existe (mismo código de activación), la devuelve
    directamente sin volver a descargar.
    """
    nombre_escena = f"copernicus-{codigo}-{fecha_desastre}"

    # Si ya la descargamos, no repetir
    existentes = escenas_copernicus()
    for e in existentes:
        if e["escena"] == nombre_escena:
            return e

    resultado = obtener_par_imagenes(
        codigo_activacion=codigo,
        lat_min=lat_min, lon_min=lon_min,
        lat_max=lat_max, lon_max=lon_max,
        fecha_desastre=fecha_desastre,
        dias_antes=dias_antes,
        dias_despues=dias_despues,
    )

    escena = {
        "escena": nombre_escena,
        "codigo_activacion": codigo,
        "titulo": titulo or codigo,
        "tipo_desastre": tipo_desastre or "emergencia",
        "fecha_desastre": fecha_desastre,
        "ruta_pre": str(resultado["pre"]),
        "ruta_post": str(resultado["post"]),
        "info_pre": resultado["info_pre"],
        "info_post": resultado["info_post"],
        "fuente": "copernicus",
    }

    existentes.append(escena)
    _guardar_metadata(existentes)

    return escena
