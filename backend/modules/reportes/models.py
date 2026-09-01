"""Acceso a datos de los reportes locales.

Comparten tabla con las sugerencias de la IA: lo que los distingue es la
columna "origen".
"""
from db.database import get_cursor
from modules.deteccion.models import _fila_a_dict


def crear_reporte(datos: dict) -> dict:
    """Guarda un reporte hecho por una persona y lo devuelve completo."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO sugerencias
               (escena, edificio_uid, dano, confianza, latitud, longitud,
                estado, origen, categoria, descripcion, reportado_por,
                capturada_en, coherencia, coherencia_explicacion, coherencia_puntuacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datos["escena"],
                datos["edificio_uid"],
                datos["dano"],
                1.0,
                datos["latitud"],
                datos["longitud"],
                datos["estado"],
                datos["origen"],
                datos["categoria"],
                datos["descripcion"],
                datos["reportado_por"],
                datos.get("capturada_en", ""),
                datos.get("coherencia", ""),
                datos.get("coherencia_explicacion", ""),
                datos.get("coherencia_puntuacion", 0.0),
            ),
        )
        fila = cursor.execute(
            "SELECT * FROM sugerencias WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return _fila_a_dict(fila)


def listar_reportes(escena: str | None = None, categoria: str | None = None):
    """Solo los puntos aportados por personas."""

    consulta = "SELECT * FROM sugerencias WHERE origen = 'persona'"
    parametros: list = []

    if escena:
        consulta += " AND escena = ?"
        parametros.append(escena)
    if categoria:
        consulta += " AND categoria = ?"
        parametros.append(categoria)

    consulta += " ORDER BY id DESC"

    with get_cursor() as cursor:
        filas = cursor.execute(consulta, parametros).fetchall()
    return [_fila_a_dict(f) for f in filas]


def contar_por_origen(escena: str | None = None) -> dict:
    """Cuántos puntos vienen de la IA y cuántos de personas.

    Es el dato que permite enseñar en la demo que las dos fuentes se
    complementan, en vez de que una sustituya a la otra.
    """
    consulta = "SELECT origen, COUNT(*) AS total FROM sugerencias"
    parametros: list = []
    if escena:
        consulta += " WHERE escena = ?"
        parametros.append(escena)
    consulta += " GROUP BY origen"

    with get_cursor() as cursor:
        filas = cursor.execute(consulta, parametros).fetchall()

    resumen = {"ia": 0, "persona": 0}
    for fila in filas:
        resumen[fila["origen"]] = fila["total"]
    return resumen
