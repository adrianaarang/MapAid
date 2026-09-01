"""Reglas de negocio del módulo de detección.

Orquesta el análisis: carga la escena, pasa cada edificio por el
comparador y guarda el resultado como sugerencias PENDIENTES.

Ninguna sugerencia sale de aquí confirmada. Esa es la regla central de
MapAid y vive en esta capa para que routes.py no pueda saltársela.
"""
from modules.deteccion import models
from modules.deteccion.comparador import (
    comparar_edificio,
    parse_wkt_polygon,
    polygon_centroid,
)
from modules.deteccion.schemas import SuggestionStatus
from modules.deteccion.xbd_loader import SceneNotFound, cargar_escena, listar_escenas

__all__ = [
    "SceneNotFound",
    "escenas_disponibles",
    "analizar_escena",
    "listar_sugerencias",
    "obtener_sugerencia",
    "resumen_por_estado",
]


def escenas_disponibles() -> list[dict]:
    return listar_escenas()


def analizar_escena(escena: str) -> dict:
    """Compara el par de imágenes y guarda las sugerencias detectadas.

    Solo se guardan los edificios en los que el comparador aprecia algún
    cambio: registrar los cientos de edificios intactos llenaría la cola
    de revisión de ruido y haría el trabajo humano inviable.
    """
    datos = cargar_escena(escena)
    metadata = datos["metadata"]
    capturada_en = metadata.get("capture_date", "")[:10]

    sugerencias = []
    for edificio in datos["edificios"]:
        poligono_px = parse_wkt_polygon(edificio["wkt_px"])
        nivel, confianza = comparar_edificio(
            datos["imagen_antes"], datos["imagen_despues"], poligono_px
        )

        if nivel.value == "no-damage":
            continue

        # El centroide geográfico da la posición del marcador en el mapa.
        # En WKT las coordenadas van (longitud, latitud), en ese orden.
        lon, lat = polygon_centroid(parse_wkt_polygon(edificio["wkt_geo"]))

        sugerencias.append(
            {
                "escena": escena,
                "edificio_uid": edificio["uid"],
                "dano": nivel.value,
                "confianza": confianza,
                "latitud": lat,
                "longitud": lon,
                "capturada_en": capturada_en,
            }
        )

    guardadas = models.guardar_sugerencias(sugerencias)

    return {
        "escena": escena,
        "detectadas": guardadas,
        "tipo_desastre": metadata.get("disaster_type", ""),
    }


def listar_sugerencias(escena=None, estado=None, dano=None) -> list[dict]:
    return models.listar_sugerencias(escena=escena, estado=estado, dano=dano)


def obtener_sugerencia(sugerencia_id: int) -> dict | None:
    return models.obtener_sugerencia(sugerencia_id)


def resumen_por_estado(escena=None) -> dict:
    return models.resumen_por_estado(escena=escena)
