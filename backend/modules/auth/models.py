"""Acceso a datos del módulo de autenticación."""
from db.database import get_cursor


def obtener_usuario_por_email(email: str) -> dict | None:
    with get_cursor() as cursor:
        fila = cursor.execute(
            "SELECT * FROM usuarios WHERE email = ? AND activo = 1",
            (email.lower().strip(),),
        ).fetchone()
    return dict(fila) if fila else None


def obtener_usuario_por_id(usuario_id: int) -> dict | None:
    with get_cursor() as cursor:
        fila = cursor.execute(
            "SELECT * FROM usuarios WHERE id = ? AND activo = 1",
            (usuario_id,),
        ).fetchone()
    return dict(fila) if fila else None
