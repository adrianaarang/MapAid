<!-- README.md -->
<div align="center">

<img src="frontend/assets/logo-mapaid-pin.png" alt="MapAid logo" width="80"/>

# MapAid

**Mapear para ayudar**

*Imágenes de satélite + conocimiento local + validación humana*

[![Tests](https://img.shields.io/badge/tests-45%20passing-1F9E7A?style=flat-square)](tests/)
[![Python](https://img.shields.io/badge/python-3.12-092E4E?style=flat-square)](backend/)
[![IoU](https://img.shields.io/badge/modelo%20xBD-IoU%200.198-FA4531?style=flat-square)](backend/ia/)

</div>

---

## Qué hace

Tras un desastre natural, los mapas quedan desactualizados. MapAid combina tres fuentes de información para reconstruirlos de forma rápida y fiable:

```
🛰  Satélite (Copernicus)  →  la IA detecta cambios en imágenes pre/post
🧭  Personas sobre el terreno  →  reportan lo que ven, la IA lo cruza con el satélite
✅  Validación humana  →  nada llega al mapa sin que una persona lo confirme
```

---

## Equipo

| | Quién | Área |
|---|---|---|
| 🗄️ | **Elena** | Datos: dataset xBD, cliente Copernicus, esquema de base de datos |
| ⚙️ | **Gema** | Backend: endpoints de detección, validación y reportes |
| 🤖 | **Adriana** | IA: modelo entrenado con xBD · cruce observación-satélite en tiempo real |
| 🗺️ | **Josema** | Mapa: Leaflet sobre OpenStreetMap, capas por estado y origen |
| 🖥️ | **Helen** | Interfaz: tarjeta de validación, formulario de reporte, cola de revisión |

---

## La IA en dos piezas

### Pieza 1 — Comparador de imágenes
Modelo **U-Net (ResNet34)** entrenado con **4.000+ pares** de imágenes de satélite del dataset xBD. Compara la imagen pre-desastre con la post-desastre y detecta qué edificios han cambiado.

```
IoU de validación: 0.198   ·   GPU Kaggle P100   ·   30 épocas   ·   tier1 + tier3
```

### Pieza 2 — Cruce observación-satélite
Cuando alguien reporta algo desde el terreno, el sistema descarga imágenes de **Sentinel-2 en tiempo real** de esa zona exacta y usa el modelo para detectar si hay daño real.

```
✅ Coherente      →  el modelo detecta daño en la zona marcada
⚠️  Posible        →  indicios leves, no concluyente
🔍 Sin cambios    →  el satélite no confirma, el reporte sigue válido
```

---

## Arquitectura

```
backend/
├── modules/
│   ├── deteccion/     sugerencias de la IA sobre imágenes Copernicus
│   ├── validacion/    confirmación · rechazo · corrección humana
│   └── reportes/      observaciones de personas + cruce satelital
├── integrations/      clientes externos (Copernicus CEMS · Overpass/OSM)
├── ia/                modelo de detección (modelo_danos.pt)
└── db/                esquema · migraciones · seed

frontend/
├── pages/
│   ├── mapa.html              app principal (login + cooperante + administradora)
│   └── reporte-publico.html   sin login — para vecinos
└── js/core/
    ├── mapa/          Leaflet + capas por estado y origen
    ├── validacion/    tarjeta antes/después y cola de revisión
    └── reportes/      formulario de reporte

data/
├── raw/xbd/           imágenes xBD (no versionadas → ver docs/datos.md)
└── processed/         resultados del entrenamiento

notebooks/             entrenamiento del modelo (Kaggle)
tests/                 pruebas backend y frontend
```

---

## Roles y acceso

| Rol | Acceso | Puede hacer |
|---|---|---|
| **Vecino / invitado** | Sin login — URL directa | Reportar lo que ve. Sin mapa ni sugerencias de IA |
| **Cooperante** | `cooperante@mapaid.com` | Ver mapa completo · reportar · **no puede validar** |
| **Administradora** | `admin@mapaid.com` | Todo lo anterior · validar sugerencias · gestionar activaciones Copernicus |

> Las contraseñas (`cooperante1234` / `admin1234`) son para entorno de demo. Cambiarlas antes de producción.

---

## Fuentes de datos

| Fuente | Uso |
|---|---|
| **Copernicus CEMS** | Imágenes oficiales pre/post desastre · activaciones de emergencia |
| **Sentinel-2 (Copernicus Data Space)** | Imágenes en tiempo real para el cruce de reportes |
| **xBD / xView2** | Entrenamiento y evaluación del modelo de daños |
| **OpenStreetMap** | Mapa base (Overpass API) |

---

## Puesta en marcha

```powershell
# Backend
cd backend
pip install -r requirements.txt
copy .env.example .env        # rellenar credenciales Copernicus y JWT_SECRET
python -m db.seed
python -m uvicorn main:app --reload --port 8000

# Frontend (desde la RAÍZ del proyecto)
python -m http.server 5500
```

| URL | Descripción |
|---|---|
| http://localhost:5500/frontend/pages/mapa.html | App principal |
| http://localhost:5500/frontend/pages/reporte-publico.html | Página de vecinos |
| http://localhost:8000/docs | Documentación interactiva de la API |

---

## Pruebas

```powershell
PYTHONPATH=backend python -m pytest tests/ -v
# 45 tests · backend · detección · validación · reportes · auth
```

---

## Variables de entorno

```env
DATABASE_PATH=./mapaid.db
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
COPERNICUS_USER=tu-email@copernicus.eu
COPERNICUS_PASSWORD=tu-contraseña          # nunca en el repo
JWT_SECRET=cambia-esto-en-produccion
MODEL_PATH=./ia/modelo_danos.pt
DATA_RAW_DIR=../data/raw
DATA_PROCESSED_DIR=../data/processed
```

---

## Reentrenar el modelo

El notebook `notebooks/MapAid_Entrenamiento_Kaggle.ipynb` está listo para ejecutarse en **Kaggle** con GPU P100 (gratuita).

1. Sube el notebook a Kaggle → New Notebook → Import Notebook
2. Panel derecho → **Add data** → buscar `qianlanzz/xbd-dataset`
3. **Session options** → **GPU P100**
4. Ejecutar todas las celdas (~3-4 horas)
5. Panel derecho → **Output** → descargar `modelo_danos.pt`
6. Copiar en `backend/ia/modelo_danos.pt`

El backend lo detecta automáticamente al arrancar.

> Resultado obtenido: **IoU 0.198** con tier1 + tier3, ResNet34, 30 épocas, GPU P100.

---

<div align="center">
<sub>MapAid · Imágenes Copernicus · Validación humana obligatoria</sub>
</div>
