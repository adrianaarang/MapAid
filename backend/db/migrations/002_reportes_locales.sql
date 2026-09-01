-- Reportes creados por personas, no por la IA.
--
-- Amplía la tabla de sugerencias en vez de crear una nueva: un punto en
-- el mapa es un punto en el mapa, lo haya visto una máquina o un vecino.
-- Lo que cambia es su origen y qué se puede hacer con él.
--
-- OJO: el script de migraciones parte los archivos por punto y coma, así
-- que no se pueden escribir puntos y coma dentro de los comentarios.

-- Quién originó el punto. Los de la IA nacen "pendiente" y necesitan
-- revisión. Los de una persona local nacen ya "confirmada": quien lo
-- reporta es testigo directo, no hace falta que otro le dé el visto bueno.
ALTER TABLE sugerencias ADD COLUMN origen TEXT NOT NULL DEFAULT 'ia';

-- Qué se está reportando. La IA solo produce daños. Una persona puede
-- reportar además recursos disponibles para ayudar, que es lo que pedía
-- el punto 1 del pitch y algo que ninguna imagen de satélite ve.
ALTER TABLE sugerencias ADD COLUMN categoria TEXT NOT NULL DEFAULT 'dano';

-- Texto libre de quien reporta. La IA lo deja vacío.
ALTER TABLE sugerencias ADD COLUMN descripcion TEXT NOT NULL DEFAULT '';

-- Quién lo reportó, para poder contrastarlo después.
ALTER TABLE sugerencias ADD COLUMN reportado_por TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_sugerencias_origen ON sugerencias (origen);

CREATE INDEX IF NOT EXISTS idx_sugerencias_categoria ON sugerencias (categoria);
