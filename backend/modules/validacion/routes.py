"""Endpoints del módulo de validación."""
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from modules.auth.routes import solo_administradora, usuario_actual
from modules.auth.schemas import UserInfo
from modules.validacion.schemas import ValidationRequest
from modules.validacion.services import (
    AlreadyReviewed,
    NotReviewable,
    SuggestionNotFound,
    cola_de_revision,
    historial,
    validar,
)

router = APIRouter(prefix="/api/validacion", tags=["validacion"])


@router.get("/pendientes")
def get_pendientes(
    escena: str | None = Query(default=None),
    _: UserInfo = Depends(usuario_actual),
):
    """Cola de sugerencias esperando revisión humana.
    Requiere autenticación (cualquier rol puede ver la cola).
    """
    return cola_de_revision(escena=escena)


@router.patch("/{sugerencia_id}")
def patch_validar(
    sugerencia_id: int,
    payload: ValidationRequest,
    _: UserInfo = Depends(solo_administradora),
):
    """Confirma, rechaza o corrige una sugerencia.
    Solo la administradora puede hacerlo.
    """
    try:
        return validar(sugerencia_id, payload)
    except SuggestionNotFound as error:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Sugerencia no encontrada", "detalle": str(error)},
        )
    except AlreadyReviewed as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "Sugerencia ya revisada", "detalle": str(error)},
        )
    except NotReviewable as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "No necesita validación", "detalle": str(error)},
        )


@router.get("/{sugerencia_id}/historial")
def get_historial(
    sugerencia_id: int,
    _: UserInfo = Depends(usuario_actual),
):
    """Quién revisó esta sugerencia, cuándo y por qué."""
    return historial(sugerencia_id)
