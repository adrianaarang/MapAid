"""Reglas de negocio de los reportes locales.

Regla central: un reporte de una persona nace pendiente y necesita que
una administradora lo revise antes de publicarse como válido.

Lo que sí hace la IA (pieza 2) es cruzar la descripción con las
imágenes de satélite y añadir un campo "coherencia" al reporte. Eso
da más contexto a la administradora al revisar — pero no decide nada.
"""
import uuid
from pathlib import Path

from config import DATA_RAW_DIR
from modules.deteccion.schemas import SuggestionStatus
from modules.reportes import models
from modules.reportes.schemas import LocalReportRequest, ReportCategory, ReportOrigin

__all__ = ["crear_reporte", "listar_reportes", "contar_por_origen"]


def _rutas_escena(escena: str) -> tuple[Path | None, Path | None, dict]:
    """Busca las imágenes pre/post y el bounding box de una escena.

    Primero busca en xBD, luego en Copernicus. Si no encuentra nada
    devuelve (None, None, {}) y el cruce se marca como no_detectable.
    """
    xbd_dir = Path(DATA_RAW_DIR) / "xbd" / "images"
    pre = xbd_dir / f"{escena}_pre_disaster.png"
    post = xbd_dir / f"{escena}_post_disaster.png"
    if pre.exists() and post.exists():
        # Las imágenes xBD no tienen bounding box registrado —
        # el cruce no puede hacerse por coordenadas.
        return pre, post, {}

    # Buscar en escenas de Copernicus descargadas
    import json
    meta_file = Path(DATA_RAW_DIR) / "copernicus" / "escenas.json"
    if meta_file.exists():
        try:
            escenas = json.loads(meta_file.read_text(encoding="utf-8"))
            for e in escenas:
                if e["escena"] == escena:
                    bbox = {
                        "lat_min": e.get("lat_min", 0),
                        "lon_min": e.get("lon_min", 0),
                        "lat_max": e.get("lat_max", 0),
                        "lon_max": e.get("lon_max", 0),
                    }
                    return Path(e["ruta_pre"]), Path(e["ruta_post"]), bbox
        except (json.JSONDecodeError, OSError):
            pass

    return None, None, {}


def _ejecutar_cruce(
    descripcion: str,
    latitud: float,
    longitud: float,
    escena: str,
) -> dict:
    """Ejecuta la pieza 2 de la IA y devuelve el resultado como dict.

    Si algo falla (imágenes no disponibles, escena de xBD sin bbox, etc.)
    devuelve coherencia="no_detectable" con una explicación, sin romper.
    """
    try:
        from modules.reportes.cruce_observacion import cruzar_observacion

        ruta_pre, ruta_post, bbox = _rutas_escena(escena)

        if ruta_pre is None or not bbox:
            return {
                "coherencia": "no_detectable",
                "puntuacion_cambio": 0.0,
                "categoria_detectada": "general",
                "explicacion": (
                    "El cruce con imágenes de satélite no está disponible "
                    "para esta escena. El reporte se guarda igualmente."
                ),
            }

        resultado = cruzar_observacion(
            descripcion=descripcion,
            lat_punto=latitud,
            lon_punto=longitud,
            ruta_pre=ruta_pre,
            ruta_post=ruta_post,
            **bbox,
        )
        return {
            "coherencia": resultado.coherencia,
            "puntuacion_cambio": resultado.puntuacion_cambio,
            "categoria_detectada": resultado.categoria_detectada,
            "explicacion": resultado.explicacion,
        }
    except Exception as error:
        return {
            "coherencia": "no_detectable",
            "puntuacion_cambio": 0.0,
            "categoria_detectada": "general",
            "explicacion": f"Cruce no disponible: {error}",
        }


def crear_reporte(peticion: LocalReportRequest, publico: bool = False) -> dict:
    """Registra lo que ha visto una persona y cruza con el satélite.

    El campo 'coherencia' que añade la IA da contexto a la administradora
    al revisar, pero no decide nada. Todos los reportes nacen pendientes.
    """
    edificio_uid = f"local-{uuid.uuid4().hex[:12]}"

    dano = (
        peticion.damage.value
        if peticion.category == ReportCategory.DAMAGE and peticion.damage
        else "un-classified"
    )

    # Todos los reportes de personas nacen pendientes — la administradora
    # siempre revisa antes de que cuenten como válidos en el mapa.
    estado = SuggestionStatus.PENDING.value

    # Pieza 2 de la IA: cruzar descripción con imágenes de satélite
    cruce = _ejecutar_cruce(
        descripcion=peticion.description,
        latitud=peticion.latitude,
        longitud=peticion.longitude,
        escena=peticion.scene,
    )

    reporte = models.crear_reporte({
        "escena": peticion.scene,
        "edificio_uid": edificio_uid,
        "dano": dano,
        "latitud": peticion.latitude,
        "longitud": peticion.longitude,
        "estado": estado,
        "origen": ReportOrigin.PERSON.value,
        "categoria": peticion.category.value,
        "descripcion": peticion.description.strip(),
        "reportado_por": peticion.reported_by.strip() or "vecino/a anónimo",
        "coherencia": cruce["coherencia"],
        "coherencia_explicacion": cruce["explicacion"],
        "coherencia_puntuacion": cruce["puntuacion_cambio"],
    })

    return reporte


def listar_reportes(escena=None, categoria=None) -> list[dict]:
    return models.listar_reportes(escena=escena, categoria=categoria)


def contar_por_origen(escena=None) -> dict:
    return models.contar_por_origen(escena=escena)
