# Fuentes de datos

Los datos NO se versionan en git (pesan demasiado). Cada persona los
descarga en su máquina siguiendo estas instrucciones.

## xBD / xView2 — imágenes antes/después

Pares de imágenes de satélite de desastres reales, con daños etiquetados.
Requiere registro gratuito en la web de xView2.

Descargar en: `data/raw/xbd/`

TODO (Elena): añadir el enlace exacto y qué subconjunto usamos (con todo
el dataset no cabe; elegir uno o dos desastres concretos).

## OpenStreetMap — mapa base (Overpass API)

Estado del terreno antes del desastre: edificios y carreteras ya
mapeados. Se descarga por zona con la Overpass API.

TODO (Elena): documentar la consulta Overpass que usamos y la zona
elegida.

## Atribución obligatoria

OpenStreetMap exige mostrar la atribución en el mapa:
`© OpenStreetMap contributors`. No quitarla.
