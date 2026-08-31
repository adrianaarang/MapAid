# MapAid — Mapear para ayudar

Reto 2 — Humanitarian OpenStreetMap Team (HOT)

Tras una emergencia el territorio cambia, pero el mapa oficial tarda en
reflejarlo. MapAid compara imágenes de satélite de antes y después del
desastre, sugiere qué ha cambiado (edificios dañados, carreteras cortadas,
estructuras nuevas) y deja que **una persona confirme, rechace o corrija**
cada sugerencia antes de darla por válida.

La IA acelera el trabajo; nunca decide sola.

---

## Estado

🚧 En desarrollo — estructura inicial del repositorio.

## Equipo

| Quién | Área |
|---|---|
| Elena | Datos: dataset xBD, Overpass API (OSM), esquema de la base de datos |
| Gema | Backend: endpoints de detección y validación |
| Adriana | IA: comparación de imágenes antes/después |
| Josema | Mapa: visualización sobre OpenStreetMap con capas de estado |
| Helen | Interfaz: tarjeta de validación y flujo de revisión humana |

## Arquitectura

```
backend/          API en FastAPI
  modules/
    deteccion/    comparación de imágenes y generación de sugerencias
    validacion/   aceptar / rechazar / corregir una sugerencia
  integrations/   clientes de fuentes externas (Overpass API de OSM)
  db/             esquema y migraciones
frontend/         HTML/CSS/JS sin framework
  js/core/
    mapa/         mapa Leaflet sobre teselas de OpenStreetMap
    validacion/   tarjeta antes/después y panel de revisión
data/
  raw/            datos descargados sin procesar (no se versionan)
  processed/      pares de imágenes ya preparados (no se versionan)
tests/            pruebas de backend y frontend
docs/             documentación del proyecto
```

## Fuentes de datos

- **OpenStreetMap** (vía Overpass API) — mapa base y estado del terreno
  antes del desastre. Datos abiertos, mantenidos por comunidades locales.
- **xBD / xView2** — pares de imágenes de satélite antes/después de
  desastres reales, con daños ya etiquetados.

MapAid **no escribe nada en el OpenStreetMap público**. Las validaciones
se guardan en la propia aplicación, igual que HOT revisa en su Tasking
Manager antes de publicar.

## Puesta en marcha

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Frontend (en otra terminal, desde frontend/)
python -m http.server 5500
```

Abrir http://localhost:5500/pages/mapa.html

Copiar `backend/.env.example` a `backend/.env` antes de arrancar.

## Pruebas

```bash
PYTHONPATH=backend python -m pytest tests/
```

## Consideraciones éticas

- **Validación humana obligatoria:** ninguna sugerencia de la IA cuenta
  como confirmada hasta que una persona la revisa.
- **Límites declarados:** el modelo no detecta daño estructural interno
  ni interiores destruidos bajo techos intactos. Se dice abiertamente.
- **Frescura del dato:** cada sugerencia lleva fecha; pasado un tiempo se
  marca como pendiente de reconfirmar.
- **Conocimiento local:** OSM lo mantienen comunidades locales; MapAid
  se apoya en su trabajo, no lo sustituye.
