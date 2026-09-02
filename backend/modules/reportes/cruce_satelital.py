"""Cruce observación-satélite usando imágenes Sentinel-2 en tiempo real.

Cuando alguien reporta algo, este módulo:
1. Busca en Copernicus Data Space las imágenes Sentinel-2 de esa zona
2. Descarga una región pequeña (recorte de ~5km) antes y después
3. Usa el modelo entrenado con xBD para predecir si hay daño real
4. Si el modelo no está disponible, cae al comparador de píxeles
5. Devuelve: coherente / posible / no_detectable + explicación
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass

import numpy as np
import requests
from PIL import Image

from config import COPERNICUS_PASSWORD, COPERNICUS_USER

_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)

_UMBRAL_COHERENTE = 0.30
_UMBRAL_POSIBLE   = 0.15

_KEYWORDS = {
    "derrumbe": ["derrumbe","derrumbado","caído","colapso","destruido","escombros","hundido","derruido"],
    "inundacion": ["agua","inundado","anegado","río","desbordado","barro","lodazal","marea","rotura","tubería"],
    "incendio": ["fuego","incendio","quemado","ceniza","humo","ardiendo","chamuscado"],
    "bloqueo": ["cortado","bloqueado","obstruido","árbol caído","barricada"],
}

_cache_token: dict = {}


@dataclass
class ResultadoCruce:
    coherencia: str
    puntuacion: float
    categoria: str
    explicacion: str


def _get_token() -> str:
    ahora = time.time()
    if _cache_token.get("exp", 0) > ahora + 300:
        return _cache_token["tok"]
    r = requests.post(_TOKEN_URL, data={
        "grant_type": "password",
        "client_id": "cdse-public",
        "username": COPERNICUS_USER,
        "password": COPERNICUS_PASSWORD,
    }, timeout=30)
    r.raise_for_status()
    datos = r.json()
    _cache_token["tok"] = datos["access_token"]
    _cache_token["exp"] = ahora + datos.get("expires_in", 600)
    return _cache_token["tok"]


def _descargar_recorte(
    lat: float, lon: float,
    fecha_inicio: str, fecha_fin: str,
) -> Image.Image | None:
    delta = 0.005  # ~500m — área más pequeña para menos falsos positivos
    bbox = [lon - delta, lat - delta, lon + delta, lat + delta]

    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{fecha_inicio}T00:00:00Z",
                        "to": f"{fecha_fin}T23:59:59Z",
                    },
                    "maxCloudCoverage": 30,
                    "mosaickingOrder": "leastCC",
                },
            }],
        },
        "output": {
            "width": 512, "height": 512,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": """
            //VERSION=3
            function setup() { return { input: ["B04","B03","B02","CLM"], output: { bands: 3 } }; }
            function evaluatePixel(s) {
                if (s.CLM == 1) return [0.5, 0.5, 0.5];
                return [3.5*s.B04, 3.5*s.B03, 3.5*s.B02];
            }
        """,
    }

    try:
        token = _get_token()
        r = requests.post(
            _PROCESS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def _detectar_categoria(texto: str) -> str:
    texto_l = texto.lower()
    for cat, palabras in _KEYWORDS.items():
        if any(p in texto_l for p in palabras):
            return cat
    return "general"


def _analizar_con_modelo(img_pre: Image.Image, img_post: Image.Image) -> dict | None:
    """Usa el modelo entrenado con xBD para detectar daños."""
    try:
        import torch
        from config import MODEL_PATH
        from pathlib import Path

        ruta = Path(MODEL_PATH)
        if not ruta.exists():
            return None

        import segmentation_models_pytorch as smp

        dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        modelo = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=6,
            classes=5,
            activation=None,
        )
        modelo.load_state_dict(torch.load(ruta, map_location=dispositivo))
        modelo.eval()
        modelo.to(dispositivo)

        # Preparar entrada: concatenar pre+post en 6 canales
        arr_pre  = np.asarray(img_pre.resize((512, 512)),  dtype=np.float32) / 255.0
        arr_post = np.asarray(img_post.resize((512, 512)), dtype=np.float32) / 255.0
        entrada  = np.concatenate([arr_pre, arr_post], axis=2)
        tensor   = torch.from_numpy(entrada.transpose(2, 0, 1)).unsqueeze(0).to(dispositivo)

        with torch.no_grad():
            logits = modelo(tensor)
            probs  = logits.softmax(1)
            pred   = probs.argmax(1)[0].cpu().numpy()

        # Calcular porcentaje de píxeles dañados (clases 1-4)
        total_pixeles = pred.size
        danados = np.isin(pred, [1, 2, 3]).sum()
        destruidos = (pred == 3).sum()
        pct_danados = danados / total_pixeles

        # Clase dominante entre los dañados
        if danados == 0:
            return {"puntuacion": 0.0, "clase_dominante": 0, "pct_danados": 0.0}

        clases_danadas = pred[np.isin(pred, [1, 2, 3])]
        clase_dominante = int(np.bincount(clases_danadas).argmax())

        return {
            "puntuacion": float(pct_danados),
            "clase_dominante": clase_dominante,
            "pct_danados": float(pct_danados),
            "pct_destruidos": float(destruidos / total_pixeles),
        }

    except Exception as e:
        return None


def _puntuacion_pixeles(img_pre: Image.Image, img_post: Image.Image) -> float:
    """Comparador de píxeles como fallback."""
    a = np.asarray(img_pre,  dtype=np.float32)
    b = np.asarray(img_post, dtype=np.float32)
    dif_brillo  = abs(float(a.mean()) - float(b.mean())) / 255.0
    dif_textura = abs(float(a.std())  - float(b.std()))  / 255.0
    return float(min(1.0, (0.65 * dif_brillo + 0.35 * dif_textura) * 2.2))


def cruzar_con_satelite(
    descripcion: str,
    lat: float,
    lon: float,
    fecha_desastre: str,
    dias_antes: int = 60,
) -> ResultadoCruce:
    from datetime import datetime, timedelta

    categoria = _detectar_categoria(descripcion)

    fecha_dt    = datetime.strptime(fecha_desastre, "%Y-%m-%d")
    pre_inicio  = (fecha_dt - timedelta(days=dias_antes)).strftime("%Y-%m-%d")
    pre_fin     = (fecha_dt - timedelta(days=5)).strftime("%Y-%m-%d")
    post_inicio = fecha_desastre
    post_fin    = (fecha_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    img_pre  = _descargar_recorte(lat, lon, pre_inicio,  pre_fin)
    img_post = _descargar_recorte(lat, lon, post_inicio, post_fin)

    if img_pre is None or img_post is None:
        return ResultadoCruce(
            coherencia="no_detectable",
            puntuacion=0.0,
            categoria=categoria,
            explicacion=(
                "No se pudieron obtener imágenes de Sentinel-2 para esta zona "
                "(puede haber nubes o la zona no tiene cobertura reciente). "
                "El reporte queda pendiente de validación humana."
            ),
        )

    # Intentar con el modelo entrenado primero
    resultado_modelo = _analizar_con_modelo(img_pre, img_post)

    if resultado_modelo is not None:
        pct = resultado_modelo["pct_danados"]
        pct_dest = resultado_modelo.get("pct_destruidos", 0)

        NOMBRES_CLASE = {1: "daño menor", 2: "daño mayor", 3: "destruido", 4: "sin clasificar"}
        clase = resultado_modelo.get("clase_dominante", 1)
        nombre_clase = NOMBRES_CLASE.get(clase, "daño")

        if pct >= 0.15:  # más del 15% de píxeles dañados — daño significativo
            coherencia = "coherente"
            explicacion = (
                f"El modelo de IA entrenado con imágenes de satélite detecta "
                f"{pct*100:.1f}% de píxeles con signos de {nombre_clase} en la zona marcada. "
                f"Coherente con lo reportado. Pendiente de confirmación humana."
            )
        elif pct >= 0.05:  # entre 5% y 15% — indicios leves
            coherencia = "posible"
            explicacion = (
                f"El modelo detecta indicios de daño ({pct*100:.1f}% de píxeles) "
                f"en la zona marcada. Posiblemente coherente con lo reportado, "
                f"pero no es concluyente. Hace falta verificación in situ."
            )
        else:
            coherencia = "no_detectable"
            explicacion = (
                f"El modelo no detecta signos de daño en la zona marcada "
                f"({pct*100:.1f}% de píxeles afectados). "
                f"Esto no significa que el reporte sea falso — muchos daños "
                f"no son visibles desde el satélite. Pendiente de validación humana."
            )

        return ResultadoCruce(
            coherencia=coherencia,
            puntuacion=round(pct, 3),
            categoria=categoria,
            explicacion=explicacion,
        )

    # Fallback: comparador de píxeles
    puntuacion = _puntuacion_pixeles(img_pre, img_post)

    if puntuacion >= _UMBRAL_COHERENTE:
        coherencia = "posible"
        explicacion = (
            f"Se detectan cambios en la zona ({int(puntuacion*100)}%). "
            f"No se pudo usar el modelo de IA — resultado aproximado. "
            f"Pendiente de validación humana."
        )
    else:
        coherencia = "no_detectable"
        explicacion = (
            f"No se detectan cambios significativos en la zona. "
            f"Pendiente de validación humana."
        )

    return ResultadoCruce(
        coherencia=coherencia,
        puntuacion=round(puntuacion, 3),
        categoria=categoria,
        explicacion=explicacion,
    )
