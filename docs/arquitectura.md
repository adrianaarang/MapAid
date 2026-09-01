# Arquitectura

## Flujo principal

1. Se elige una escena (un par de imágenes pre/post ya descargado).
2. `POST /api/deteccion/analizar` recorta cada edificio en las dos
   imágenes y mide cuánto ha cambiado (`comparador.py`).
3. Los cambios se guardan como **sugerencias en estado `pendiente`**.
4. El mapa las pinta sobre OpenStreetMap, cada estado en su capa.
5. Una persona revisa cada una: confirmar, rechazar o corregir.
6. Solo las confirmadas cuentan como cambio real.

## La regla que no se salta

**Ninguna sugerencia se confirma sola.** La IA solo puede crear
sugerencias en estado `pendiente`; el único camino para cambiar ese
estado pasa por `modules/validacion/services.py`, que exige una acción
humana explícita. Además:

- Una sugerencia solo se puede revisar **una vez**: si ya la miró
  alguien, un segundo intento devuelve 409 en vez de sobrescribir su
  decisión en silencio.
- Rechazar y corregir **exigen motivo**. Sin él no se podría estudiar
  después en qué se equivoca la IA.
- Cada decisión queda registrada en la tabla `validaciones` con quién y
  cuándo.

## Capas

```
routes.py    → HTTP: recibe peticiones, traduce errores a códigos
services.py  → reglas de negocio (aquí vive la regla de arriba)
models.py    → SQL parametrizado
```

`routes.py` nunca llama a `models.py` directamente: siempre pasa por
`services.py`, para que las reglas no se puedan esquivar por accidente.

## Sobre el comparador (la IA)

Es visión por computador clásica, no una red neuronal: compara brillo y
textura de cada edificio entre las dos imágenes. Se eligió a propósito
por ser explicable, determinista y no necesitar entrenamiento ni GPU.

Medido contra las etiquetas reales de xBD en las escenas de ejemplo:
detecta en torno al 44-62% de los edificios dañados, con alrededor de un
18% de falsos positivos.

Esos números **no son un fallo del diseño, son el argumento**: una
herramienta así no puede publicar nada por su cuenta. Sirve para que una
persona revise 30 candidatos en vez de 600 edificios uno a uno.

Lo que no detecta está documentado en el docstring de `comparador.py`:
daño interno con el tejado intacto, y se confunde con sombras, nubes y
cambios de ángulo o de hora entre capturas.

## Convenciones

- Nombres internos en inglés, contrato JSON público en español.
- SQL siempre parametrizado.
- Los `.sql` de migraciones se parten por `;`, así que no se pueden
  escribir puntos y coma dentro de los comentarios.
- Una rama por persona: `feature/<modulo>/<nombre>`, PR contra `dev`.

## Dos fuentes, un mismo mapa

MapAid guarda en la misma tabla los puntos detectados por la IA y los
reportados por personas. Lo que los distingue es la columna `origen`:

| | IA (`origen = "ia"`) | Persona (`origen = "persona"`) |
|---|---|---|
| Nace | `pendiente` | `confirmada` |
| Confianza | estimada (0.35–0.92) | 1.0 (testimonio directo) |
| Categorías | solo `dano` | `dano`, `recurso`, `acceso` |
| ¿Pasa por revisión? | sí, obligatoria | no |
| En el mapa | círculo, color por estado | cuadrado, color por categoría |

### Por qué un reporte local no se valida

Puede parecer que contradice la regla central ("nada se confirma sin
persona"), pero es justo lo contrario. Esa regla existe para que ninguna
**máquina** dé por buenas sus propias conjeturas. En un reporte local ya
hay una persona: la que está viéndolo. Pedirle que un segundo humano
valide su testimonio convertiría el conocimiento local en algo sospechoso
por defecto — lo contrario de "sin perder el conocimiento y control de
las personas locales".

Lo que sí se guarda siempre es **quién** lo reportó, para poder
contrastarlo si algo no cuadra.

Intentar validar un reporte local devuelve **409**, y esos reportes nunca
aparecen en la cola de revisión.
