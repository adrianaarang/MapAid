"""Reglas de negocio de la validación humana.

Reglas:
- Una sugerencia solo se puede revisar una vez (409 si ya revisada).
- Los reportes locales (origen=persona) no se pueden validar aquí (409).
- Rechazar y corregir exigen motivo.

TODO (Gema).
"""
