# Fuentes de datos

## xBD / xView2 — imágenes antes/después

Pares de imágenes de satélite de desastres reales (1024x1024 px), con los
edificios delimitados y su nivel de daño ya etiquetado por especialistas.

Descarga: https://xview2.org/ (requiere registro gratuito y aceptar la
licencia). Del archivo que se descarga solo hacen falta las carpetas
`images/` y `labels/` del subconjunto **test** o **hold** — los de
entrenamiento (`train`, `tier1`, `tier3`) pesan decenas de GB y no se
usan aquí, porque MapAid no entrena ningún modelo.

Colocar los archivos así:

```
data/raw/xbd/
  images/
    <escena>_pre_disaster.png
    <escena>_post_disaster.png
  labels/
    <escena>_pre_disaster.json
    <escena>_post_disaster.json
```

El repositorio ya incluye cuatro escenas de ejemplo (un tsunami, una
inundación y un incendio) para poder arrancar sin descargar nada.

### Qué se usa de cada archivo

- **`_pre_disaster.png` / `_post_disaster.png`**: las dos imágenes que
  compara la IA.
- **`_post_disaster.json`**: de aquí sale la lista de edificios. Cada uno
  trae su polígono en píxeles (`features.xy`, para recortar la imagen) y
  en coordenadas geográficas (`features.lng_lat`, para pintarlo en el
  mapa), más un `uid` que permite seguirlo entre las dos imágenes.
- El campo `subtype` de las etiquetas (el daño real anotado a mano) **no
  se usa para decidir**: se conserva solo para poder medir después cuánto
  acierta el comparador.

### Escala de daño

MapAid reutiliza la escala oficial de xBD sin traducirla, para que las
etiquetas reales encajen directamente:

| Valor | Significado |
|---|---|
| `no-damage` | Sin señales de daño |
| `minor-damage` | Parcialmente quemado, agua alrededor, grietas visibles |
| `major-damage` | Colapso parcial de muro o techo, rodeado de agua o barro |
| `destroyed` | Calcinado, colapsado, o ya no está |
| `un-classified` | No se pudo determinar |

## OpenStreetMap

El mapa base son las teselas de OSM, cargadas con Leaflet. La atribución
`© OpenStreetMap contributors` es obligatoria por licencia y está puesta
en `mapaCambios.js`: **no quitarla**.

`backend/integrations/overpass_client.py` está preparado para descargar
edificios reales de OSM con la Overpass API. En la demo actual el papel
de "mapa antes del desastre" lo hacen las etiquetas de xBD, que ya vienen
georreferenciadas y no dependen de una llamada de red en directo.

MapAid **no escribe nada en el OpenStreetMap público**: las validaciones
se guardan en la base de datos local, igual que HOT revisa en su Tasking
Manager antes de publicar.
