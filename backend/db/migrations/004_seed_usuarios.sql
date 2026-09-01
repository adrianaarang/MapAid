-- Usuarios iniciales de MapAid.
-- Contraseñas en bcrypt: admin1234 y cooperante1234.
-- Cambiarlas antes de producción real.

INSERT OR IGNORE INTO usuarios (email, password_hash, rol) VALUES
('admin@mapaid.com', '$2b$12$SWq5Nn9MzkpsZIBLfCoHluYJTE7gi7COiFntskA/70nEAtzDM/6pS', 'administradora'),
('cooperante@mapaid.com', '$2b$12$SKQ/EgsxMh.DR5Owo0S5ter1xgrnU4PhdoIKorTUnFgjLuhX9i4zu', 'cooperante');
