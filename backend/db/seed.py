"""Analiza todas las escenas disponibles, para tener datos con los que probar.

Uso, desde backend/ y con el entorno activado:

    python db/seed.py

No inventa datos: ejecuta el mismo análisis que la API sobre las escenas
que haya en data/raw/xbd. Es idempotente — volver a lanzarlo no duplica
sugerencias ni pisa las que ya haya validado una persona.
"""
import sys
from pathlib import Path

# Al lanzar el script directamente ("python db/seed.py"), Python solo
# pone db/ en sys.path, no backend/, así que los imports de abajo
# fallarían. Se añade backend/ a mano para que funcione tanto así como
# con "python -m db.seed".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import init_db  # noqa: E402
from modules.deteccion.services import analizar_escena, escenas_disponibles  # noqa: E402


def main() -> None:
    init_db()

    escenas = escenas_disponibles()
    if not escenas:
        print("No hay escenas en data/raw/xbd. Ver docs/datos.md.")
        return

    total = 0
    for escena in escenas:
        resultado = analizar_escena(escena["escena"])
        total += resultado["detectadas"]
        print(
            f"  {resultado['escena']:38s} "
            f"{resultado['tipo_desastre']:10s} "
            f"{resultado['detectadas']:3d} sugerencias"
        )

    print(f"\n{total} sugerencias pendientes de revisión humana.")


if __name__ == "__main__":
    main()
