# Arquitectura

## Flujo principal

1. Se parte de un par de imágenes (antes / después) de una zona.
2. El comparador (`modules/deteccion/comparador.py`) detecta regiones
   que han cambiado y genera **sugerencias** en estado `pendiente`.
3. Las sugerencias se pintan sobre el mapa de OpenStreetMap.
4. Una persona revisa cada una: confirmar, rechazar o corregir.
5. Solo las confirmadas cuentan como cambio real.

## Regla que no se salta

`routes.py` nunca habla directamente con `models.py`: siempre pasa por
`services.py`. Así las reglas de negocio (sobre todo "nada se confirma
sin persona") no se pueden esquivar por accidente.

## Convenciones

- Nombres internos en inglés, contrato JSON de la API en español.
- Consultas SQL siempre parametrizadas.
- Una rama por persona: `feature/<modulo>/<nombre>`.
- PR contra `dev`, con al menos una revisión antes de mergear.

TODO: completar según vayamos decidiendo.
