"""Conexión a SQLite y ejecución de migraciones."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(config.DATABASE_PATH)
    # sqlite3.Row permite acceder por nombre de columna, lo que evita
    # depender del orden de los campos en las consultas.
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def get_cursor():
    """Cursor con commit automático, o rollback si algo falla."""

    conexion = _conectar()
    try:
        cursor = conexion.cursor()
        yield cursor
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def init_db() -> None:
    """Aplica en orden todos los .sql de migrations/.

    Se ignoran los errores de "ya existe" (duplicate column / table) para
    que arrancar dos veces seguidas no rompa nada: las migraciones son
    idempotentes a propósito.
    """
    with get_cursor() as cursor:
        for migracion in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = migracion.read_text(encoding="utf-8")
            for sentencia in sql.split(";"):
                sentencia = sentencia.strip()
                if not sentencia:
                    continue
                try:
                    cursor.execute(sentencia)
                except sqlite3.OperationalError as error:
                    if "already exists" in str(error) or "duplicate column" in str(error):
                        continue
                    raise
