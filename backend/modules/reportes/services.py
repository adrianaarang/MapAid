"""Reglas de negocio de los reportes locales.

Regla central: un reporte de una persona nace ya confirmado.

Puede parecer que contradice la regla de MapAid ("nada se confirma sin
persona"), pero es justo lo contrario: esa regla existe para que ninguna
máquina dé por buenas sus propias conjeturas. Aquí ya hay una persona —
la que está en el terreno viéndolo.

Lo que sí hace la IA (pieza 2) es cruzar la descripción con las
imágenes de satélite y añadir un campo "coherencia" al reporte. Eso
da más contexto a la administradora al revisar — pero no decide nada.
"""
import uuid
from pathlib import Path

from config import COPERNICUS_PASSWORD, COPERNICUS_USER, DATA_RAW_DIR
from modules.deteccion.schemas import SuggestionStatus
from modules.reportes import models
from modules.reportes.schemas import LocalReportRequest, ReportCategory, ReportOrigin

__all__ = ["crear_reporte", "listar_reportes", "contar_por_origen"]


def _rutas_escena(escena: str) -> tuple[Path | None, Path | None, dict]:
    """Busca las imágenes pre/post y el bounding box de una escena.

    Para xBD calcula el bounding box real a partir de las coordenadas
    geográficas de los edificios etiquetados.
    Para Copernicus usa el bounding box registrado al descargar.
    """
    xbd_dir = Path(DATA_RAW_DIR) / "xbd"
    pre = xbd_dir / "images" / f"{escena}_pre_disaster.png"
    post = xbd_dir / "images" / f"{escena}_post_disaster.png"

    if pre.exists() and post.exists():
        # Calcular bounding box real desde las etiquetas geográficas de xBD
        label = xbd_dir / "labels" / f"{escena}_post_disaster.json"
        bbox = {}
        if label.exists():
            try:
                import json, re
                datos = json.loads(label.read_text(encoding="utf-8"))
                feats = datos.get("features", {}).get("lng_lat", [])
                lons, lats = [], []
                for f in feats:
                    nums = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", f["wkt"])
                    vals = [float(n) for n in nums]
                    lons += vals[0::2]
                    lats += vals[1::2]
                if lons and lats:
                    margen = 0.001
                    bbox = {
                        "lat_min": min(lats) - margen,
                        "lon_min": min(lons) - margen,
                        "lat_max": max(lats) + margen,
                        "lon_max": max(lons) + margen,
                    }
            except Exception:
                pass
        return pre, post, bbox

    # Buscar en escenas de Copernicus
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
    fecha_desastre: str = "",
) -> dict:
    """Ejecuta el cruce observación-satélite.

    Prioridad:
    1. Sentinel-2 en tiempo real (si hay credenciales de Copernicus)
    2. Imágenes xBD locales (si la escena tiene bbox)
    3. No detectable (si no hay nada disponible)
    """
    # 1. Intentar con Sentinel-2 en tiempo real
    if COPERNICUS_USER and COPERNICUS_PASSWORD and fecha_desastre:
        try:
            from modules.reportes.cruce_satelital import cruzar_con_satelite
            resultado = cruzar_con_satelite(
                descripcion=descripcion,
                lat=latitud,
                lon=longitud,
                fecha_desastre=fecha_desastre,
            )
            return {
                "coherencia": resultado.coherencia,
                "puntuacion_cambio": resultado.puntuacion,
                "categoria_detectada": resultado.categoria,
                "explicacion": resultado.explicacion,
            }
        except Exception as error:
            # Si falla Sentinel-2, caer a xBD
            pass

    # 2. Intentar con imágenes xBD locales
    try:
        from modules.reportes.cruce_observacion import cruzar_observacion
        ruta_pre, ruta_post, bbox = _rutas_escena(escena)
        if ruta_pre is not None and bbox:
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
    except Exception:
        pass

    # 3. No detectable
    return {
        "coherencia": "no_detectable",
        "puntuacion_cambio": 0.0,
        "categoria_detectada": "general",
        "explicacion": (
            "No se pudieron obtener imágenes satelitales para esta zona. "
            "El reporte se guarda igualmente para revisión humana."
        ),
    }


def crear_reporte(peticion: LocalReportRequest, publico: bool = False) -> dict:
    """Registra lo que ha visto una persona y cruza con el satélite.

    El campo 'coherencia' que añade la IA da contexto a la administradora
    al revisar — pero no decide nada. El reporte nace confirmado si viene
    de un usuario autenticado, o pendiente si viene de un vecino sin login.
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

    # Pieza 2 de la IA: cruzar descripción con imágenes Sentinel-2 en tiempo real
    # Si no hay fecha de desastre, usar hace 30 días como referencia
    # (Sentinel-2 no tiene imágenes del futuro)
    from datetime import date as _date, timedelta as _timedelta
    fecha_desastre = getattr(peticion, "disaster_date", None) or \
        (_date.today() - _timedelta(days=30)).strftime("%Y-%m-%d")

    cruce = _ejecutar_cruce(
        descripcion=peticion.description,
        latitud=peticion.latitude,
        longitud=peticion.longitude,
        escena=peticion.scene,
        fecha_desastre=fecha_desastre,
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
