"""Endpoints del módulo de detección."""
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from modules.deteccion.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    DamageLevel,
    SuggestionStatus,
)
from modules.deteccion.services import (
    SceneNotFound,
    analizar_escena,
    escenas_disponibles,
    listar_sugerencias,
    obtener_sugerencia,
    resumen_por_estado,
)

router = APIRouter(prefix="/api/deteccion", tags=["deteccion"])


@router.get("/escenas")
def get_escenas():
    """Pares de imágenes disponibles en data/raw/xbd."""

    return escenas_disponibles()


@router.post("/analizar", response_model=AnalyzeResponse)
def post_analizar(payload: AnalyzeRequest):
    """Compara el par de imágenes de una escena y genera sugerencias.

    Todas nacen en estado "pendiente": hace falta que una persona las
    revise antes de que cuenten como cambio real.
    """
    try:
        return analizar_escena(payload.scene)
    except SceneNotFound as error:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Escena no encontrada", "detalle": str(error)},
        )


@router.get("/sugerencias")
def get_sugerencias(
    escena: str | None = Query(default=None),
    estado: SuggestionStatus | None = Query(default=None),
    dano: DamageLevel | None = Query(default=None),
):
    """Lista las sugerencias, con filtros opcionales."""

    return listar_sugerencias(
        escena=escena,
        estado=estado.value if estado else None,
        dano=dano.value if dano else None,
    )


@router.get("/sugerencias/{sugerencia_id}")
def get_sugerencia(sugerencia_id: int):
    sugerencia = obtener_sugerencia(sugerencia_id)
    if sugerencia is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Sugerencia no encontrada",
                "detalle": f"No existe una sugerencia con id {sugerencia_id}.",
            },
        )
    return sugerencia


@router.get("/resumen")
def get_resumen(escena: str | None = Query(default=None)):
    """Recuento por estado, para el panel de resumen de la zona."""

    return resumen_por_estado(escena=escena)
