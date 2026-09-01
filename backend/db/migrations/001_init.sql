-- Esquema inicial de MapAid.
--
-- OJO: el script de migraciones parte los archivos por punto y coma, así
-- que no se pueden escribir puntos y coma dentro de los comentarios.

CREATE TABLE IF NOT EXISTS sugerencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Par de imágenes analizado, p. ej. "palu-tsunami_00000124"
    escena TEXT NOT NULL,
    -- uid del edificio en las etiquetas de xBD
    edificio_uid TEXT NOT NULL,
    -- Escala de daño de xBD (ver DamageLevel en schemas.py)
    dano TEXT NOT NULL CHECK (
        dano IN ('no-damage', 'minor-damage', 'major-damage', 'destroyed', 'un-classified')
    ),
    confianza REAL NOT NULL CHECK (confianza >= 0 AND confianza <= 1),
    latitud REAL NOT NULL,
    longitud REAL NOT NULL,
    -- Nace siempre como pendiente: solo una persona puede cambiarlo
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (
        estado IN ('pendiente', 'confirmada', 'rechazada', 'corregida')
    ),
    capturada_en TEXT NOT NULL DEFAULT '',
    creada_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- Una escena no puede tener dos sugerencias del mismo edificio
    UNIQUE (escena, edificio_uid)
);

CREATE INDEX IF NOT EXISTS idx_sugerencias_estado ON sugerencias (estado);

CREATE INDEX IF NOT EXISTS idx_sugerencias_escena ON sugerencias (escena);

-- Trazabilidad: quién revisó qué y por qué. Se guarda aparte de
-- sugerencias para conservar el historial aunque el estado cambie.
CREATE TABLE IF NOT EXISTS validaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sugerencia_id INTEGER NOT NULL REFERENCES sugerencias (id) ON DELETE CASCADE,
    estado_anterior TEXT NOT NULL,
    estado_nuevo TEXT NOT NULL,
    -- Al rechazar o corregir se pide motivo, para revisar patrones de error
    motivo TEXT NOT NULL DEFAULT '',
    revisada_por TEXT NOT NULL DEFAULT 'anonimo',
    revisada_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_validaciones_sugerencia ON validaciones (sugerencia_id);
