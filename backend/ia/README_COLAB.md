# Entrenamiento del modelo de detección de daños

## Pasos

1. Sube `data/raw/xbd/` a Google Drive en `Mi unidad/mapaid/data/raw/xbd/`
2. Abre `MapAid_Entrenamiento_xBD.ipynb` en Google Colab
3. Entorno de ejecución → Cambiar tipo → **GPU T4** (gratuita)
4. Ejecutar todas las celdas — tarda ~2-3 horas
5. Descarga `modelo_danos.pt` al acabar
6. Cópialo en `backend/ia/modelo_danos.pt`
7. Reinicia el backend — lo cargará automáticamente

## Qué mejora al entrenar

Sin modelo entrenado: el comparador mide diferencias de brillo/textura
→ ~44-62% de acierto, ~18% falsos positivos.

Con modelo entrenado con xBD (U-Net ResNet18): aprende qué aspecto
tienen edificios destruidos, inundados o quemados desde el satélite
→ los resultados del reto xView2 apuntan a un IoU del 60-75% en datos
nuevos, dependiendo del tipo de desastre.

## Sin el modelo

El backend funciona igual con el comparador clásico. El modelo es
una mejora, no un requisito.
