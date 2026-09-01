"""Esquemas del módulo de validación humana."""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.deteccion.schemas import DamageLevel


class ValidationAction(str, Enum):
    """Qué hace la persona con una sugerencia."""

    CONFIRM = "confirmar"
    REJECT = "rechazar"
    CORRECT = "corregir"


class ValidationRequest(BaseModel):
    """Entrada del endpoint de validación."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    action: ValidationAction = Field(alias="accion")
    # Obligatorio al rechazar o corregir: sin motivo no se puede revisar
    # después por qué falló la IA.
    reason: str = Field(default="", alias="motivo", max_length=500)
    # Solo al corregir: el nivel de daño que la persona considera correcto.
    corrected_damage: DamageLevel | None = Field(default=None, alias="dano_corregido")
    reviewer: str = Field(default="anonimo", alias="revisada_por", max_length=80)

    @model_validator(mode="after")
    def _comprobar_coherencia(self) -> "ValidationRequest":
        if self.action == ValidationAction.CORRECT and self.corrected_damage is None:
            raise ValueError("Al corregir hay que indicar 'dano_corregido'.")
        if self.action in (ValidationAction.REJECT, ValidationAction.CORRECT):
            if not self.reason.strip():
                raise ValueError("Al rechazar o corregir hay que indicar un motivo.")
        return self
