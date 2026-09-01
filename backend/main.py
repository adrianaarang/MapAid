"""Punto de entrada de la API de MapAid."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from db.database import init_db
from modules.auth.routes import router as auth_router
from modules.copernicus.routes import router as copernicus_router
from modules.deteccion.routes import router as deteccion_router
from modules.reportes.routes import router as reportes_router
from modules.validacion.routes import router as validacion_router

app = FastAPI(
    title="MapAid",
    description="Detección asistida de cambios tras un desastre. La IA sugiere, las personas confirman.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(copernicus_router)
app.include_router(deteccion_router)
app.include_router(reportes_router)
app.include_router(validacion_router)

init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
