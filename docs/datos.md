# Fuentes de datos

## Copernicus Emergency Management Service (CEMS)

Fuente principal de imágenes en producción. Publicaciones automáticas
tras cada activación de emergencia, con pares pre/post georreferenciados.

Registro gratuito: https://dataspace.copernicus.eu
Credenciales → backend/.env (variables COPERNICUS_USER y COPERNICUS_PASSWORD).

## xBD / xView2

Se usa SOLO para entrenamiento y evaluación del modelo, no como fuente
de imágenes en producción.

Descarga: https://xview2.org (registro gratuito, aceptar licencia).
Colocar en data/raw/xbd/images/ y data/raw/xbd/labels/.
Solo hace falta el subconjunto train para entrenar; test/hold para evaluar.

Ver backend/ia/README_COLAB.md para instrucciones de entrenamiento.

## OpenStreetMap (Overpass API)

Mapa base: edificios y carreteras antes del desastre.
Atribución obligatoria en el mapa: © OpenStreetMap contributors.
