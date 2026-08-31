"""Analiza las escenas disponibles para generar datos de prueba.

Uso (desde backend/, con el entorno activado):
    python -m db.seed

TODO (Elena): llamar a init_db() y a analizar_escena() para cada escena
disponible en data/raw/xbd/.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
