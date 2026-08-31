# Arquitectura de MapAid

## Flujo principal

1. Copernicus publica imágenes pre/post del desastre.
2. La IA (pieza 1, modelo entrenado con xBD) detecta edificios dañados
   → sugerencia PENDIENTE.
3. Una persona describe lo que ve → la IA (pieza 2) cruza la descripción
   con la imagen Copernicus → sugerencia PENDIENTE con campo "coherencia".
4. Un revisor/a confirma, rechaza o corrige cada sugerencia.
5. Solo las confirmadas aparecen en el mapa como cambio real.

## La regla que no se salta

routes.py → services.py → models.py (nunca routes → models directamente).
La IA nunca confirma sus propias sugerencias.
Una sugerencia solo se puede revisar una vez (409 si ya revisada).
Los reportes locales no pasan por la cola de validación.

## Convenciones

- Nombres internos en inglés, contrato JSON público en español.
- SQL siempre parametrizado.
- Una rama por persona: feature/<modulo>/<nombre>, PR contra dev.
