# Entrenamiento del modelo en Google Colab

El modelo de detección de daños se entrena con el dataset xBD usando
PyTorch. Se ejecuta en Google Colab (GPU gratuita T4), tarda ~2-3 horas
con el subconjunto `train` de xBD.

## Pasos

1. Subir la carpeta `data/raw/xbd/` a Google Drive.
2. Abrir `ia/entrenamiento.ipynb` en Colab.
3. Conectar con GPU: Entorno de ejecución → Cambiar tipo → T4 GPU.
4. Ejecutar todas las celdas.
5. Descargar `modelo_danos.pt` y copiarlo en `backend/ia/`.

## Arquitectura del modelo

Red U-Net ligera con encoder ResNet18 preentrenado en ImageNet.
Entrada: par de imágenes (pre + post) de 512x512 px.
Salida: máscara de daño por píxel con 5 clases (escala xBD).

TODO (Adriana): implementar entrenamiento.ipynb con la arquitectura
y el pipeline de datos de xBD.
