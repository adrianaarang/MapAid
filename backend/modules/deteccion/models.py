"""Acceso a datos del módulo de detección.

Todas las consultas van parametrizadas: nunca se concatena texto que
venga de fuera dentro del SQL.
"""
from db.database import get_cursor
from modules.deteccion.schemas import DAMAGE_LABELS, DamageLevel


def _fila_a_dict(fila) -> dict:
    """Convierte una fila de SQLite al contrato JSON público (español)."""

    datos = dict(fila)
    nivel = DamageLevel(datos["dano"])
    datos["dano_etiqueta"] = DAMAGE_LABELS[nivel]
    return datos


def guardar_sugerencias(sugerencias: list[dict]) -> int:
    """Inserta las sugerencias de una escena.

    Si una escena se reanaliza, las sugerencias ya existentes se ignoran
    (UNIQUE escena+edificio) en vez de duplicarse: reanalizar no debe
    borrar el trabajo de validación ya hecho por una persona.
    """
    if not sugerencias:
        return 0

    with get_cursor() as cursor:
        cursor.executemany(
            """INSERT OR IGNORE INTO sugerencias
               (escena, edificio_uid, dano, confianza, latitud, longitud, capturada_en)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    s["escena"],
                    s["edificio_uid"],
                    s["dano"],
                    s["confianza"],
                    s["latitud"],
                    s["longitud"],
                    s.get("capturada_en", ""),
                )
                for s in sugerencias
            ],
        )
        return cursor.rowcount


def listar_sugerencias(
    escena: str | None = None,
    estado: str | None = None,
    dano: str | None = None,
) -> list[dict]:
    """Lista sugerencias con filtros opcionales combinables."""

    consulta = "SELECT * FROM sugerencias WHERE 1 = 1"
    parametros: list = []

    if escena:
        consulta += " AND escena = ?"
        parametros.append(escena)
    if estado:
        consulta += " AND estado = ?"
        parametros.append(estado)
    if dano:
        consulta += " AND dano = ?"
        parametros.append(dano)

    consulta += " ORDER BY confianza DESC, id ASC"

    with get_cursor() as cursor:
        filas = cursor.execute(consulta, parametros).fetchall()
    return [_fila_a_dict(f) for f in filas]


def obtener_sugerencia(sugerencia_id: int) -> dict | None:
    with get_cursor() as cursor:
        fila = cursor.execute(
            "SELECT * FROM sugerencias WHERE id = ?", (sugerencia_id,)
        ).fetchone()
    return _fila_a_dict(fila) if fila else None


def resumen_por_estado(escena: str | None = None) -> dict:
    """Cuántas sugerencias hay en cada estado (para el panel de resumen)."""

    consulta = "SELECT estado, COUNT(*) AS total FROM sugerencias"
    parametros: list = []
    if escena:
        consulta += " WHERE escena = ?"
        parametros.append(escena)
    consulta += " GROUP BY estado"

    with get_cursor() as cursor:
        filas = cursor.execute(consulta, parametros).fetchall()

    resumen = {"pendiente": 0, "confirmada": 0, "rechazada": 0, "corregida": 0}
    for fila in filas:
        resumen[fila["estado"]] = fila["total"]
    return resumen
