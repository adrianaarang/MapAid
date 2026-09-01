-- Guardar el resultado del cruce observación-satélite (pieza 2 de la IA)
-- directamente en la fila del reporte para no perderlo.

ALTER TABLE sugerencias ADD COLUMN coherencia TEXT NOT NULL DEFAULT '';
ALTER TABLE sugerencias ADD COLUMN coherencia_explicacion TEXT NOT NULL DEFAULT '';
ALTER TABLE sugerencias ADD COLUMN coherencia_puntuacion REAL NOT NULL DEFAULT 0.0
