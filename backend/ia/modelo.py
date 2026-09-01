"""Inferencia del modelo de detección de daños entrenado con xBD.

Cuando existe backend/ia/modelo_danos.pt (generado por el notebook de Colab),
este módulo lo carga y lo usa en vez del comparador de píxeles clásico.
Si no existe, el sistema cae de vuelta al comparador clásico sin romper.

Escala de clases (igual que en el notebook):
  0 → sin daño
  1 → daño menor
  2 → daño mayor
  3 → destruido
  4 → sin clasificar
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from config import MODEL_PATH
from modules.deteccion.schemas import DamageLevel

_CLASE_A_NIVEL = {
    0: DamageLevel.NO_DAMAGE,
    1: DamageLevel.MINOR,
    2: DamageLevel.MAJOR,
    3: DamageLevel.DESTROYED,
    4: DamageLevel.UNCLASSIFIED,
}

_modelo = None
_dispositivo = None
_modelo_intentado = False


def _cargar_modelo():
    """Carga el modelo PyTorch si está disponible. Solo intenta una vez."""
    global _modelo, _dispositivo, _modelo_intentado
    if _modelo_intentado:
        return _modelo
    _modelo_intentado = True

    ruta = Path(MODEL_PATH)
    if not ruta.exists():
        return None

    try:
        import torch
        import segmentation_models_pytorch as smp

        _dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        red = smp.Unet(
            encoder_name="resnet18",
            encoder_weights=None,
            in_channels=6,
            classes=5,
            activation=None,
        )
        red.load_state_dict(torch.load(ruta, map_location=_dispositivo))
        red.eval()
        red.to(_dispositivo)
        _modelo = red
        print(f"✅ Modelo xBD cargado desde {ruta} ({_dispositivo})")
        return _modelo
    except Exception as error:
        print(f"⚠️  No se pudo cargar el modelo: {error}. Usando comparador clásico.")
        return None


def inferir_edificio(
    img_antes: Image.Image,
    img_despues: Image.Image,
    bbox: tuple[int, int, int, int],
) -> tuple[DamageLevel, float] | None:
    """Predice el nivel de daño de un edificio usando el modelo entrenado.

    Args:
        img_antes/img_despues: imágenes completas de la escena.
        bbox: (izq, arr, der, aba) en píxeles del edificio.

    Returns:
        (DamageLevel, confianza) si el modelo está disponible,
        None si hay que usar el comparador clásico.
    """
    red = _cargar_modelo()
    if red is None:
        return None

    try:
        import torch

        tamano = 512
        izq, arr, der, aba = bbox
        recorte_pre  = img_antes.crop(bbox).resize((tamano, tamano))
        recorte_post = img_despues.crop(bbox).resize((tamano, tamano))

        arr_pre  = np.asarray(recorte_pre,  dtype=np.float32) / 255.0
        arr_post = np.asarray(recorte_post, dtype=np.float32) / 255.0

        # 6 canales: 3 del pre + 3 del post
        entrada = np.concatenate([arr_pre, arr_post], axis=2)
        tensor = torch.from_numpy(entrada.transpose(2, 0, 1)).unsqueeze(0).to(_dispositivo)

        with torch.no_grad():
            logits = red(tensor)            # (1, 5, H, W)
            probs  = logits.softmax(1)      # probabilidades por clase
            pred   = probs.argmax(1)        # clase más probable por píxel

        # Clase dominante en la región del edificio
        clases = pred[0].cpu().numpy().flatten()
        clase_dominante = int(np.bincount(clases, minlength=5)[1:].argmax()) + 1

        confianza = float(probs[0, clase_dominante].mean().cpu())
        confianza = min(0.95, max(0.35, confianza))

        return _CLASE_A_NIVEL.get(clase_dominante, DamageLevel.UNCLASSIFIED), round(confianza, 2)

    except Exception as error:
        print(f"⚠️  Error en inferencia: {error}")
        return None
