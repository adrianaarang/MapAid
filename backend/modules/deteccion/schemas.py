"""Esquemas del módulo de detección.

Define la forma de una sugerencia de cambio detectada al comparar una
imagen de antes y otra de después de un desastre.

Los nombres internos van en inglés; los alias mantienen el contrato JSON
público en español, que es lo que consume el frontend.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DamageLevel(str, Enum):
    """Escala de daño oficial del dataset xBD.

    Se replica tal cual (mismos valores que el campo "subtype" de los
    JSON de xBD) para que las etiquetas reales encajen sin traducción.
    """

    NO_DAMAGE = "no-damage"
    MINOR = "minor-damage"
    MAJOR = "major-damage"
    DESTROYED = "destroyed"
    UNCLASSIFIED = "un-classified"


# Etiqueta legible en español, lista para pintar en la interfaz. Vive
# aquí para que el frontend no mantenga su propia copia del mapeo.
DAMAGE_LABELS: dict[DamageLevel, str] = {
    DamageLevel.NO_DAMAGE: "Sin daño",
    DamageLevel.MINOR: "Daño menor",
    DamageLevel.MAJOR: "Daño mayor",
    DamageLevel.DESTROYED: "Destruido",
    DamageLevel.UNCLASSIFIED: "Sin clasificar",
}


class SuggestionStatus(str, Enum):
    """Ciclo de vida de una sugerencia.

    Nace siempre como "pendiente". Solo una persona puede sacarla de ahí
    (ver modules/validacion): la IA nunca confirma sus propias sugerencias.
    """

    PENDING = "pendiente"
    CONFIRMED = "confirmada"
    REJECTED = "rechazada"
    CORRECTED = "corregida"


class Suggestion(BaseModel):
    """Una sugerencia de cambio en un edificio concreto."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: int = Field(gt=0)
    # Identificador del par analizado, p. ej. "palu-tsunami_00000124".
    scene: str = Field(alias="escena")
    # uid del edificio en las etiquetas de xBD, para poder rastrearlo.
    building_uid: str = Field(alias="edificio_uid")

    damage: DamageLevel = Field(alias="dano")
    damage_label: str = Field(default="", alias="dano_etiqueta")
    # 0-1: cuánta diferencia encontró el comparador entre antes y después.
    confidence: float = Field(alias="confianza", ge=0, le=1)

    latitude: float = Field(alias="latitud", ge=-90, le=90)
    longitude: float = Field(alias="longitud", ge=-180, le=180)

    status: SuggestionStatus = Field(alias="estado")
    # "ia" o "persona": permite al mapa distinguir lo detectado
    # automáticamente de lo aportado por gente sobre el terreno.
    origin: str = Field(default="ia", alias="origen")
    category: str = Field(default="dano", alias="categoria")
    description: str = Field(default="", alias="descripcion")
    reported_by: str = Field(default="", alias="reportado_por")
    # Fecha de captura de la imagen posterior (metadata de xBD).
    captured_at: str = Field(default="", alias="capturada_en")
    created_at: datetime = Field(alias="creada_en")


class AnalyzeRequest(BaseModel):
    """Entrada para analizar un par de imágenes ya presente en data/raw."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scene: str = Field(alias="escena", min_length=3, max_length=120)


class AnalyzeResponse(BaseModel):
    """Resultado de analizar una escena."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scene: str = Field(alias="escena")
    detected: int = Field(alias="detectadas")
    disaster_type: str = Field(default="", alias="tipo_desastre")
