# MapAid — Mapear para ayudar

Reto 2 — Humanitarian OpenStreetMap Team (HOT)

Tras una emergencia el territorio cambia, pero el mapa oficial tarda en
reflejarlo. MapAid compara imágenes de satélite de antes y después del
desastre, sugiere qué edificios han quedado dañados, y deja que **una
persona confirme, rechace o corrija** cada sugerencia.

**La IA acelera el trabajo; nunca decide sola.**

---

## Qué hace, en concreto

MapAid junta dos fuentes que se complementan: lo que la máquina detecta y
lo que solo sabe quien está allí.

**La IA propone:**
1. Toma un par de imágenes de la misma zona (antes / después) del
   dataset **xBD**.
2. Recorta cada edificio en las dos imágenes y mide cuánto ha cambiado
   su brillo y su textura.
3. Genera sugerencias de daño (menor / mayor / destruido) con un nivel
   de confianza, **todas en estado `pendiente`**.
4. Las pinta sobre **OpenStreetMap** en su posición geográfica real.
5. Una persona revisa la cola y decide. Solo entonces cuenta como cambio.

**Las personas aportan:**
6. Cualquiera sobre el terreno puede marcar un punto en el mapa y
   reportar lo que ve: un **daño** que a la IA se le escapó, un **recurso
   disponible** (un pozo que funciona, un centro de acogida) o un
   **acceso bloqueado** (un puente cortado).
7. Esos reportes **nacen ya confirmados**: quien los escribe es testigo
   directo. No se les exige que un segundo humano valide lo que han visto
   con sus propios ojos — eso trataría el conocimiento local como
   sospechoso por defecto, justo lo contrario de lo que pide el reto.
8. En el mapa se distinguen por forma (cuadrados) y color, no solo por
   color, para que se vean sin depender de distinguir tonos.

Un satélite nunca verá si un pozo da agua potable. Una persona en Palu,
sí.

## Honestidad sobre el modelo

El comparador es visión por computador clásica, no una red neuronal
entrenada: se eligió por ser explicable, determinista y no necesitar GPU.

Medido contra las etiquetas reales de xBD:

| Escena | Daños detectados | Falsos positivos |
|---|---|---|
| palu-tsunami_00000124 | 22 / 50 (44%) | 11 / 61 (18%) |
| hurricane-florence_00000113 | 16 / 26 (62%) | 0 |

**Esos números son el argumento, no el problema.** Una herramienta con
esa precisión no puede publicar nada por su cuenta — pero sí convierte
"revisar 600 edificios uno a uno" en "revisar 33 candidatos". Por eso la
validación humana es obligatoria, no un extra.

Lo que **no** detecta: daño interno con el tejado intacto, y se confunde
con sombras, nubes y cambios de ángulo entre capturas.

## Equipo

| Quién | Área |
|---|---|
| Elena | Datos: dataset xBD, Overpass API, esquema de la base de datos |
| Gema | Backend: endpoints de detección y validación |
| Adriana | IA: comparación de imágenes antes/después |
| Josema | Mapa: visualización sobre OpenStreetMap con capas de estado |
| Helen | Interfaz: tarjeta de validación y flujo de revisión |

## Arquitectura

```
backend/
  modules/
    deteccion/    comparador de imágenes + carga de escenas xBD
    validacion/   confirmar / rechazar / corregir (revisión humana)
    reportes/     lo que aportan las personas sobre el terreno
  integrations/   cliente de la Overpass API de OpenStreetMap
  db/             esquema, migraciones y script de análisis inicial
frontend/
  js/core/
    mapa/         Leaflet sobre teselas de OSM, una capa por estado
    validacion/   tarjeta antes/después y cola de revisión
    reportes/     formulario para reportar lo que se ve
data/raw/xbd/     imágenes y etiquetas (ver docs/datos.md)
tests/            43 pruebas de backend
```

Documentación ampliada en [`docs/arquitectura.md`](docs/arquitectura.md)
y [`docs/datos.md`](docs/datos.md).

## Puesta en marcha

```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Analizar las escenas de ejemplo (opcional pero recomendado)
python db/seed.py

python -m uvicorn main:app --reload --port 8000
```

```bash
# 2. Frontend, en otra terminal, desde la raíz del proyecto
python -m http.server 5500
```

Abrir **http://localhost:5500/frontend/pages/mapa.html**

> El servidor se lanza desde la raíz (no desde `frontend/`) para que las
> miniaturas puedan leer las imágenes de `data/raw/`.

Documentación interactiva de la API: http://localhost:8000/docs

## Pruebas

```bash
PYTHONPATH=backend python -m pytest tests/
```

## API

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/deteccion/escenas` | Pares de imágenes disponibles |
| POST | `/api/deteccion/analizar` | Compara un par y genera sugerencias |
| GET | `/api/deteccion/sugerencias` | Lista, con filtros por escena/estado/daño |
| GET | `/api/deteccion/resumen` | Recuento por estado |
| GET | `/api/validacion/pendientes` | Cola de revisión |
| PATCH | `/api/validacion/{id}` | Confirmar / rechazar / corregir |
| GET | `/api/validacion/{id}/historial` | Quién revisó qué y por qué |
| POST | `/api/reportes` | Reportar algo visto sobre el terreno |
| GET | `/api/reportes` | Lista los reportes de personas |
| GET | `/api/reportes/origen` | Cuántos puntos vienen de la IA y cuántos de personas |

## Consideraciones éticas

- **Validación humana obligatoria.** Ninguna sugerencia se confirma sola,
  y una vez revisada no se puede sobrescribir en silencio (devuelve 409).
- **Motivo obligatorio** al rechazar o corregir: es lo que permite
  estudiar después en qué falla la IA.
- **Trazabilidad.** Cada decisión guarda quién y cuándo.
- **Límites declarados**, en el README y en el código, no escondidos.
- **Frescura del dato.** Cada sugerencia guarda la fecha de captura de la
  imagen que la originó.
- **Conocimiento local.** OSM lo mantienen comunidades locales; MapAid se
  apoya en su trabajo y **no escribe nada** en el OSM público.
- **Las personas no solo corrigen, también aportan.** Pueden añadir al
  mapa lo que ninguna imagen de satélite muestra. Sus reportes no pasan
  por validación de terceros, y el sistema nunca los mezcla con los de la
  IA: cada punto dice de dónde viene.
