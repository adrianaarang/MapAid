-- Tabla de usuarios con roles fijos.
-- No hay registro público: las cuentas las crea la administradora.
-- Las contraseñas se guardan con hash bcrypt, nunca en texto plano.

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('cooperante', 'administradora')),
    activo INTEGER NOT NULL DEFAULT 1,
    creado_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email)
