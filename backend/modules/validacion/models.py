"""Acceso a datos del módulo de validación."""
from db.database import get_cursor


def aplicar_validacion(
    sugerencia_id: int,
    estado_anterior: str,
    estado_nuevo: str,
    motivo: str,
    revisada_por: str,
    dano_corregido: str | None = None,
) -> dict | None:
    """Cambia el estado de una sugerencia y deja constancia de quién fue.

    Las dos escrituras van en la misma transacción: no puede quedar una
    sugerencia validada sin su registro de trazabilidad.
    """
    with get_cursor() as cursor:
        if dano_corregido:
            cursor.execute(
                "UPDATE sugerencias SET estado = ?, dano = ? WHERE id = ?",
                (estado_nuevo, dano_corregido, sugerencia_id),
            )
        else:
            cursor.execute(
                "UPDATE sugerencias SET estado = ? WHERE id = ?",
                (estado_nuevo, sugerencia_id),
            )

        if cursor.rowcount == 0:
            return None

        cursor.execute(
            """INSERT INTO validaciones
               (sugerencia_id, estado_anterior, estado_nuevo, motivo, revisada_por)
               VALUES (?, ?, ?, ?, ?)""",
            (sugerencia_id, estado_anterior, estado_nuevo, motivo, revisada_por),
        )

        fila = cursor.execute(
            "SELECT * FROM sugerencias WHERE id = ?", (sugerencia_id,)
        ).fetchone()

    return dict(fila) if fila else None


def historial(sugerencia_id: int) -> list[dict]:
    """Todas las revisiones de una sugerencia, de más antigua a más nueva."""

    with get_cursor() as cursor:
        filas = cursor.execute(
            "SELECT * FROM validaciones WHERE sugerencia_id = ? ORDER BY id ASC",
            (sugerencia_id,),
        ).fetchall()
    return [dict(f) for f in filas]
