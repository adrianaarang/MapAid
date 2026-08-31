# MapAid — Mapear para ayudar

Una IA entrenada con xBD compara imágenes de Copernicus antes/después
de un desastre y sugiere qué ha cambiado. Las personas sobre el terreno
también pueden reportar lo que ven: la IA cruza su descripción con las
imágenes de Copernicus y dice si es coherente. Nada llega al mapa sin
que una persona lo confirme.

## Equipo

| Quién | Área |
|---|---|
| Elena | Datos: xBD, cliente Copernicus, esquema BD |
| Gema | Backend: endpoints detección, validación, reportes |
| Adriana | IA: modelo entrenado (pieza 1) + cruce observación-satélite (pieza 2) |
| Josema | Mapa: Leaflet sobre OSM con imágenes Copernicus de fondo |
| Helen | Interfaz: tarjeta validación, formulario reporte, cola de revisión |

## Arquitectura

```
backend/
  modules/
    deteccion/    sugerencias de la IA sobre imágenes Copernicus
    validacion/   confirmación / rechazo / corrección humana
    reportes/     observaciones aportadas por personas
  integrations/   clientes externos (Copernicus CEMS, Overpass/OSM)
  ia/             modelo de detección de daños (entrenado con xBD)
  db/             esquema, migraciones, seed
frontend/
  js/core/
    mapa/         Leaflet + capas por estado y origen
    validacion/   tarjeta antes/después y cola de revisión
    reportes/     formulario para reportar lo que se ve
data/
  raw/xbd/        imágenes y etiquetas xBD (no se versionan, ver docs/datos.md)
  processed/      resultados del entrenamiento
docs/             arquitectura, datos, convenciones
tests/            pruebas backend y frontend
```

## Fuentes de datos

- **Copernicus CEMS** — imágenes oficiales pre/post desastre (gratuito)
- **xBD / xView2** — entrenamiento y evaluación del modelo de daños
- **OpenStreetMap** — mapa base (Overpass API)

## Puesta en marcha

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env
python -m db.seed
python -m uvicorn main:app --reload --port 8000
```

```bash
# En otra terminal, desde la RAÍZ del proyecto
python -m http.server 5500
# Abrir: http://localhost:5500/frontend/pages/mapa.html
```

## Pruebas

```bash
PYTHONPATH=backend python -m pytest tests/
```

## Entrenamiento del modelo (Google Colab)

Ver `backend/ia/README_COLAB.md` — se ejecuta en Colab con GPU gratuita,
tarda 2-3 horas con el subconjunto `train` de xBD.

