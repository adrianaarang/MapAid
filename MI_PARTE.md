# MapAid — Parte de Helen

## Tus archivos

### Páginas
- `frontend/pages/mapa.html` — app principal (login + cooperante + administradora)
- `frontend/pages/reporte-publico.html` — página para vecinos sin login

### Estilos
- `frontend/css/variables.css` — colores de marca MapAid (no tocar)
- `frontend/css/base.css` — estilos base
- `frontend/css/mapa.css` — estilos de la pantalla principal

### JavaScript
- `frontend/js/core/api.js` — todas las llamadas al backend
- `frontend/js/core/app.js` — arranque de la app
- `frontend/js/core/validacion/tarjetaValidacion.js` — tarjeta antes/después
- `frontend/js/core/validacion/colaValidacion.js` — cola de revisión
- `frontend/js/core/reportes/formularioReporte.js` — formulario de reporte

## Cómo ver la interfaz

```powershell
# En una terminal (raíz del proyecto):
python -m http.server 5500
# Abrir: http://localhost:5500/frontend/pages/mapa.html
```

El backend tiene que estar corriendo en el puerto 8000.

## Usuarios de prueba

| Email | Contraseña | Rol |
|---|---|---|
| admin@mapaid.com | admin1234 | Administradora |
| cooperante@mapaid.com | cooperante1234 | Cooperante |

## URL para vecinos (sin login)

```
http://localhost:5500/frontend/pages/reporte-publico.html
```
