"""Endpoints de los reportes locales."""
from fastapi import APIRouter, Depends, Query

from modules.auth.routes import usuario_actual
from modules.auth.schemas import UserInfo
from modules.reportes.schemas import LocalReportRequest, ReportCategory
from modules.reportes.services import contar_por_origen, crear_reporte, listar_reportes

router = APIRouter(prefix="/api/reportes", tags=["reportes"])


@router.post("/publico", status_code=201)
def post_reporte_publico(payload: LocalReportRequest):
    """Endpoint público — no requiere login.

    Cualquier vecino puede reportar lo que ve sin necesidad de cuenta.
    El reporte llega igual que los demás, con origen=persona, y la
    administradora lo ve en el mapa junto con las sugerencias de la IA.
    """
    return crear_reporte(payload)


@router.post("", status_code=201)
def post_reporte(
    payload: LocalReportRequest,
    _: UserInfo = Depends(usuario_actual),
):
    """Registra algo visto por una persona autenticada sobre el terreno."""
    return crear_reporte(payload)


@router.get("")
def get_reportes(
    escena: str | None = Query(default=None),
    categoria: ReportCategory | None = Query(default=None),
    _: UserInfo = Depends(usuario_actual),
):
    """Lista solo los puntos aportados por personas."""
    return listar_reportes(
        escena=escena,
        categoria=categoria.value if categoria else None,
    )


@router.get("/origen")
def get_origen(
    escena: str | None = Query(default=None),
    _: UserInfo = Depends(usuario_actual),
):
    """Cuántos puntos vienen de la IA y cuántos de personas."""
    return contar_por_origen(escena=escena)
