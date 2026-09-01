"""Endpoints de integración con Copernicus CEMS."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from integrations.copernicus_client import CopernicusError, listar_activaciones
from modules.auth.routes import solo_administradora, usuario_actual
from modules.auth.schemas import UserInfo
from modules.copernicus.services import descargar_escena_activacion, escenas_copernicus

router = APIRouter(prefix="/api/copernicus", tags=["copernicus"])


@router.get("/activaciones")
def get_activaciones(
    max_resultados: int = 10,
    _: UserInfo = Depends(usuario_actual),
):
    """Lista las activaciones de emergencia recientes de Copernicus CEMS."""
    try:
        return listar_activaciones(max_resultados=max_resultados)
    except CopernicusError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        )


@router.get("/escenas")
def get_escenas_copernicus(_: UserInfo = Depends(usuario_actual)):
    """Lista las escenas ya descargadas de Copernicus, listas para analizar."""
    return escenas_copernicus()


class UsarActivacionRequest(BaseModel):
    codigo: str = Field(min_length=3)
    lat_min: float
    lon_min: float
    lat_max: float
    lon_max: float
    fecha_desastre: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    titulo: str = ""
    tipo_desastre: str = ""
    dias_antes: int = Field(default=30, ge=1, le=90)
    dias_despues: int = Field(default=15, ge=1, le=60)


@router.post("/usar-activacion")
def post_usar_activacion(
    payload: UsarActivacionRequest,
    _: UserInfo = Depends(solo_administradora),
):
    """Descarga las imágenes de una activación Copernicus y la registra
    como escena disponible para analizar.

    Solo la administradora puede hacer esto. La descarga puede tardar
    varios minutos según el tamaño de la zona.

    Una vez completado, la escena aparece en GET /api/deteccion/escenas
    y se puede analizar con POST /api/deteccion/analizar.
    """
    try:
        return descargar_escena_activacion(
            codigo=payload.codigo,
            lat_min=payload.lat_min,
            lon_min=payload.lon_min,
            lat_max=payload.lat_max,
            lon_max=payload.lon_max,
            fecha_desastre=payload.fecha_desastre,
            titulo=payload.titulo,
            tipo_desastre=payload.tipo_desastre,
            dias_antes=payload.dias_antes,
            dias_despues=payload.dias_despues,
        )
    except CopernicusError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        )


class DescargarRequest(BaseModel):
    codigo_activacion: str = Field(min_length=3)
    lat_min: float; lon_min: float; lat_max: float; lon_max: float
    fecha_desastre: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    dias_antes: int = Field(default=30, ge=1, le=90)
    dias_despues: int = Field(default=15, ge=1, le=60)


@router.post("/descargar")
def post_descargar(
    payload: DescargarRequest,
    _: UserInfo = Depends(usuario_actual),
):
    """Descarga el par de imágenes pre/post de una activación Copernicus."""
    from integrations.copernicus_client import obtener_par_imagenes
    try:
        r = obtener_par_imagenes(
            codigo_activacion=payload.codigo_activacion,
            lat_min=payload.lat_min, lon_min=payload.lon_min,
            lat_max=payload.lat_max, lon_max=payload.lon_max,
            fecha_desastre=payload.fecha_desastre,
            dias_antes=payload.dias_antes, dias_despues=payload.dias_despues,
        )
        return {"escena": r["escena"], "pre": str(r["pre"]),
                "post": str(r["post"]), "info_pre": r["info_pre"], "info_post": r["info_post"]}
    except CopernicusError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
