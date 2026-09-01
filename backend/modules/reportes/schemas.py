"""Esquemas de los reportes hechos por personas.

Un reporte local es un punto que pone alguien que está en el terreno:
algo que la IA no vio (un edificio dañado que se le escapó) o algo que
ninguna imagen de satélite puede ver (un pozo que funciona, un centro de
acogida abierto, una carretera cortada por escombros).

Es la contraparte de las sugerencias automáticas: allí la máquina propone
y la persona valida; aquí la persona aporta lo que la máquina no alcanza.
"""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.deteccion.schemas import DamageLevel


class ReportOrigin(str, Enum):
    """De dónde salió un punto del mapa."""

    AI = "ia"
    PERSON = "persona"


class ReportCategory(str, Enum):
    """Qué se está reportando.

    La IA solo produce "dano": es lo único que puede deducir comparando
    dos imágenes. Las demás categorías solo puede aportarlas alguien que
    esté allí.
    """

    DAMAGE = "dano"
    # Algo disponible para ayudar: agua potable, refugio, suministros.
    RESOURCE = "recurso"
    # Un paso bloqueado: carretera cortada, puente caído.
    ACCESS = "acceso"


CATEGORY_LABELS: dict[ReportCategory, str] = {
    ReportCategory.DAMAGE: "Daño",
    ReportCategory.RESOURCE: "Recurso disponible",
    ReportCategory.ACCESS: "Acceso bloqueado",
}


class LocalReportRequest(BaseModel):
    """Entrada para crear un reporte local."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scene: str = Field(alias="escena", min_length=3, max_length=120)
    category: ReportCategory = Field(alias="categoria")

    latitude: float = Field(alias="latitud", ge=-90, le=90)
    longitude: float = Field(alias="longitud", ge=-180, le=180)

    description: str = Field(alias="descripcion", min_length=3, max_length=500)
    reported_by: str = Field(
        default="vecino anónimo", alias="reportado_por", max_length=80
    )

    # Fecha aproximada del desastre para buscar imágenes en Copernicus.
    # Si no se indica, se usa la fecha actual.
    disaster_date: str | None = Field(
        default=None, alias="fecha_desastre",
        pattern=r"^\d{4}-\d{2}-\d{2}$" if False else None,
    )

    # Solo tiene sentido al reportar un daño: un recurso disponible no
    # tiene "nivel de daño".
    damage: DamageLevel | None = Field(default=None, alias="dano")

    @model_validator(mode="after")
    def _comprobar_coherencia(self) -> "LocalReportRequest":
        if self.category == ReportCategory.DAMAGE and self.damage is None:
            raise ValueError("Al reportar un daño hay que indicar su nivel ('dano').")
        if self.category != ReportCategory.DAMAGE and self.damage is not None:
            raise ValueError(
                "El campo 'dano' solo se usa cuando la categoría es 'dano'."
            )
        return self
