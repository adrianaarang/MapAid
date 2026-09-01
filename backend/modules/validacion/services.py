"""Reglas de negocio de la validación humana.

Aquí vive la regla central de MapAid: una sugerencia solo deja de estar
pendiente si una persona la revisa. La IA nunca valida su propio trabajo.
"""
from modules.deteccion.models import listar_sugerencias
from modules.deteccion.schemas import SuggestionStatus
from modules.validacion import models
from modules.validacion.schemas import ValidationAction, ValidationRequest


class SuggestionNotFound(LookupError):
    """No existe la sugerencia que se intenta validar."""


class AlreadyReviewed(ValueError):
    """La sugerencia ya fue revisada por una persona."""


class NotReviewable(ValueError):
    """Se intenta validar algo que no lo necesita (un reporte local)."""


_ACCION_A_ESTADO = {
    ValidationAction.CONFIRM: SuggestionStatus.CONFIRMED,
    ValidationAction.REJECT: SuggestionStatus.REJECTED,
    ValidationAction.CORRECT: SuggestionStatus.CORRECTED,
}


def cola_de_revision(escena: str | None = None) -> list[dict]:
    """Sugerencias de la IA pendientes, las de mayor confianza primero.

    Se ordenan así porque son las que más probablemente reflejan un daño
    real, y conviene que una persona las mire cuanto antes.

    Los reportes locales no aparecen aquí: no están esperando el visto
    bueno de nadie.
    """
    pendientes = listar_sugerencias(
        escena=escena, estado=SuggestionStatus.PENDING.value
    )
    return [s for s in pendientes if s.get("origen", "ia") == "ia"]


def validar(sugerencia_id: int, peticion: ValidationRequest) -> dict:
    """Aplica la decisión de una persona sobre una sugerencia.

    Una sugerencia solo se puede revisar una vez: si ya la revisó alguien,
    se rechaza el intento en vez de sobrescribir su decisión en silencio.
    """
    from modules.deteccion.models import obtener_sugerencia

    sugerencia = obtener_sugerencia(sugerencia_id)
    if sugerencia is None:
        raise SuggestionNotFound(f"No existe la sugerencia {sugerencia_id}")

    # Los reportes de personas también pasan por revisión de la administradora
    # antes de publicarse — todos los reportes pendientes necesitan confirmación.

    if sugerencia["estado"] != SuggestionStatus.PENDING.value:
        raise AlreadyReviewed(
            f"La sugerencia {sugerencia_id} ya fue revisada "
            f"(estado actual: {sugerencia['estado']})"
        )

    estado_nuevo = _ACCION_A_ESTADO[peticion.action]
    dano_corregido = (
        peticion.corrected_damage.value if peticion.corrected_damage else None
    )

    actualizada = models.aplicar_validacion(
        sugerencia_id=sugerencia_id,
        estado_anterior=sugerencia["estado"],
        estado_nuevo=estado_nuevo.value,
        motivo=peticion.reason.strip(),
        revisada_por=peticion.reviewer.strip() or "anonimo",
        dano_corregido=dano_corregido,
    )

    if actualizada is None:
        raise SuggestionNotFound(f"No existe la sugerencia {sugerencia_id}")
    return actualizada


def historial(sugerencia_id: int) -> list[dict]:
    return models.historial(sugerencia_id)
