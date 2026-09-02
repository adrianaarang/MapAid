"""Lectura de las escenas de xBD desde data/raw.

Cada "escena" es un par de imágenes (pre y post) más sus etiquetas en
JSON. Las etiquetas hacen aquí el papel que en producción haría el mapa
base de OpenStreetMap: dicen dónde hay un edificio antes de que la IA
mire nada.

Nada de este módulo escribe en disco: solo lee lo que ya está descargado.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from config import DATA_RAW_DIR

_XBD_DIR = Path(DATA_RAW_DIR) / "xbd"

# Soporte para datasets con estructura tier1/tier2/tier3
# Si no hay imágenes directamente en xbd/images, buscar en tier1
_TIER1_DIR = _XBD_DIR / "tier1"
if not (_XBD_DIR / "images").is_dir() and (_TIER1_DIR / "images").is_dir():
    IMAGES_DIR = _TIER1_DIR / "images"
    LABELS_DIR = _TIER1_DIR / "labels"
else:
    IMAGES_DIR = _XBD_DIR / "images"
    LABELS_DIR = _XBD_DIR / "labels"


class SceneNotFound(FileNotFoundError):
    """La escena pedida no está descargada en data/raw/xbd."""


def _buscar_archivo(nombre: str) -> Path | None:
    """Busca un archivo en xbd/ o dentro de cualquiera de sus subcarpetas de split."""
    for split in SPLITS:
        base = _XBD_DIR / split if split else _XBD_DIR
        # Busca en ./images, ./labels o directamente en la carpeta
        candidatos = [
            base / "images" / nombre,
            base / "labels" / nombre,
            base / nombre,
        ]
        for ruta in candidatos:
            if ruta.exists():
                return ruta
    return None


def listar_escenas() -> list[dict]:
    """Escenas disponibles en disco, con su tipo de desastre.

    Solo devuelve las que tienen las cuatro piezas (imagen y etiqueta,
    antes y después); una escena incompleta no se puede analizar.
    """
    if not _XBD_DIR.is_dir():
        return []

    # Recolectar todos los archivos post_disaster.png en cualquier split
    archivos_post = []
    for split in SPLITS:
        base = _XBD_DIR / split if split else _XBD_DIR
        carpeta_imgs = base / "images"
        if carpeta_imgs.is_dir():
            archivos_post.extend(carpeta_imgs.glob("*_post_disaster.png"))
        elif base.is_dir():
            archivos_post.extend(base.glob("*_post_disaster.png"))

    escenas = []
    vistos = set()

    for post in sorted(archivos_post):
        base_nombre = post.name.replace("_post_disaster.png", "")
        if base_nombre in vistos:
            continue

        ruta_pre = _buscar_archivo(f"{base_nombre}_pre_disaster.png")
        ruta_post = post
        ruta_label = _buscar_archivo(f"{base_nombre}_post_disaster.json")

        if not ruta_pre or not ruta_post or not ruta_label:
            continue

        vistos.add(base_nombre)
        datos_json = _leer_json(ruta_label)
        metadata = datos_json.get("metadata", {})

        escenas.append(
            {
                "escena": base_nombre,
                "tipo_desastre": metadata.get("disaster_type", ""),
                "capturada_en": metadata.get("capture_date", "")[:10],
                "edificios": len(
                    datos_json.get("features", {}).get("xy", [])
                ),
            }
        )
    return escenas


def _leer_json(ruta: Path) -> dict:
    if not ruta.exists():
        raise SceneNotFound(f"No se encuentra {ruta.name} en data/raw/xbd")
    with ruta.open(encoding="utf-8") as fichero:
        return json.load(fichero)


def cargar_escena(escena: str) -> dict:
    """Devuelve imágenes, edificios y metadatos de una escena.

    Cada edificio trae su polígono en píxeles (para recortar la imagen) y
    en coordenadas geográficas (para pintarlo sobre el mapa).
    """
    ruta_pre = _buscar_archivo(f"{escena}_pre_disaster.png")
    ruta_post = _buscar_archivo(f"{escena}_post_disaster.png")
    ruta_label = _buscar_archivo(f"{escena}_post_disaster.json")

    if not ruta_pre or not ruta_post:
        raise SceneNotFound(f"Faltan imágenes de la escena {escena}")
    if not ruta_label:
        raise SceneNotFound(f"Falta el archivo de etiquetas para la escena {escena}")

    etiquetas = _leer_json(ruta_label)
    caracteristicas = etiquetas.get("features", {})
    en_pixeles = caracteristicas.get("xy", [])
    en_grados = caracteristicas.get("lng_lat", [])

    grados_por_uid = {
        elemento["properties"]["uid"]: elemento["wkt"] for elemento in en_grados
    }

    edificios = []
    for elemento in en_pixeles:
        uid = elemento["properties"]["uid"]
        if uid not in grados_por_uid:
            continue
        edificios.append(
            {
                "uid": uid,
                "subtype_real": elemento["properties"].get("subtype", ""),
                "wkt_px": elemento["wkt"],
                "wkt_geo": grados_por_uid[uid],
            }
        )

    return {
        "escena": escena,
        "imagen_antes": Image.open(ruta_pre).convert("RGB"),
        "imagen_despues": Image.open(ruta_post).convert("RGB"),
        "edificios": edificios,
        "metadata": etiquetas.get("metadata", {}),
    }