"""Cliente de la Overpass API (OpenStreetMap).

Descarga el estado del mapa ANTES del desastre para una zona: los
edificios que la comunidad de OSM ya tenía mapeados.

En la demo actual ese papel lo hacen las etiquetas de xBD, que ya vienen
georreferenciadas y no dependen de una llamada de red en directo. Este
módulo queda listo para cuando se quiera analizar una zona real que no
esté en el dataset.

Si Overpass falla o tarda, se lanza OverpassError y quien llame decide:
nunca debe tumbar la aplicación, porque es una fuente externa que no
controlamos.
"""
import requests

from config import OVERPASS_API_URL

_TIMEOUT_SEGUNDOS = 30


class OverpassError(Exception):
    """No se pudo consultar Overpass (red, límite de uso, respuesta rara)."""


def _consulta_edificios(sur: float, oeste: float, norte: float, este: float) -> str:
    """Consulta en Overpass QL: todos los edificios de un rectángulo."""

    return f"""
        [out:json][timeout:25];
        (
          way["building"]({sur},{oeste},{norte},{este});
          relation["building"]({sur},{oeste},{norte},{este});
        );
        out center;
    """


def descargar_edificios(
    sur: float, oeste: float, norte: float, este: float
) -> list[dict]:
    """Edificios mapeados en OSM dentro del rectángulo dado.

    Devuelve una lista de {osm_id, latitud, longitud}. Se usa "out center"
    en vez de la geometría completa porque para situar un marcador basta
    el centro, y la respuesta pesa mucho menos.
    """
    try:
        respuesta = requests.post(
            OVERPASS_API_URL,
            data={"data": _consulta_edificios(sur, oeste, norte, este)},
            timeout=_TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        raise OverpassError(f"No se pudo consultar Overpass: {error}") from error

    try:
        elementos = respuesta.json().get("elements", [])
    except ValueError as error:
        raise OverpassError("Overpass devolvió una respuesta ilegible") from error

    edificios = []
    for elemento in elementos:
        # Los "way" y "relation" traen su centro en la clave "center".
        centro = elemento.get("center") or {}
        lat = centro.get("lat", elemento.get("lat"))
        lon = centro.get("lon", elemento.get("lon"))
        if lat is None or lon is None:
            continue
        edificios.append(
            {"osm_id": elemento.get("id"), "latitud": lat, "longitud": lon}
        )
    return edificios
