"""Configuración leída del archivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

DATABASE_PATH = os.getenv("DATABASE_PATH", str(_BACKEND_DIR / "mapaid.db"))
BACKEND_PORT  = int(os.getenv("BACKEND_PORT", "8000"))
CORS_ORIGINS  = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500").split(",")
    if o.strip()
]

# OpenStreetMap
OVERPASS_API_URL = os.getenv(
    "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter"
)

# Datos
DATA_RAW_DIR       = os.getenv("DATA_RAW_DIR",
    str(_BACKEND_DIR.parent / "data" / "raw"))
DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR",
    str(_BACKEND_DIR.parent / "data" / "processed"))

# Modelo entrenado
MODEL_PATH = os.getenv("MODEL_PATH", str(_BACKEND_DIR / "ia" / "modelo_danos.pt"))

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "mapaid-demo-secret-2024")

# Copernicus Data Space Ecosystem
COPERNICUS_USER     = os.getenv("COPERNICUS_USER", "")
COPERNICUS_PASSWORD = os.getenv("COPERNICUS_PASSWORD", "")
