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


def listar_escenas() -> list[dict]:
    """Escenas disponibles en disco, con su tipo de desastre.

    Solo devuelve las que tienen las cuatro piezas (imagen y etiqueta,
    antes y después); una escena incompleta no se puede analizar.
    """
    if not IMAGES_DIR.is_dir():
        return []

    escenas = []
    for post in sorted(IMAGES_DIR.glob("*_post_disaster.png")):
        base = post.name.replace("_post_disaster.png", "")
        piezas = [
            IMAGES_DIR / f"{base}_pre_disaster.png",
            IMAGES_DIR / f"{base}_post_disaster.png",
            LABELS_DIR / f"{base}_post_disaster.json",
        ]
        if not all(p.exists() for p in piezas):
            continue

        metadata = _leer_json(LABELS_DIR / f"{base}_post_disaster.json").get(
            "metadata", {}
        )
        escenas.append(
            {
                "escena": base,
                "tipo_desastre": metadata.get("disaster_type", ""),
                "capturada_en": metadata.get("capture_date", "")[:10],
                "edificios": len(
                    _leer_json(LABELS_DIR / f"{base}_post_disaster.json")
                    .get("features", {})
                    .get("xy", [])
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
    ruta_pre = IMAGES_DIR / f"{escena}_pre_disaster.png"
    ruta_post = IMAGES_DIR / f"{escena}_post_disaster.png"
    if not ruta_pre.exists() or not ruta_post.exists():
        raise SceneNotFound(f"Faltan imágenes de la escena {escena}")

    etiquetas = _leer_json(LABELS_DIR / f"{escena}_post_disaster.json")
    caracteristicas = etiquetas.get("features", {})
    en_pixeles = caracteristicas.get("xy", [])
    en_grados = caracteristicas.get("lng_lat", [])

    # Se emparejan por uid y no por posición: aunque en xBD suelen venir
    # en el mismo orden, no está garantizado y un desajuste colocaría los
    # marcadores en el sitio equivocado.
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
                # Etiqueta original de xBD: NO se usa para decidir, solo
                # se guarda para poder comparar después qué acertó la IA.
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
