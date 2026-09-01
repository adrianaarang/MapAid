"""Pruebas del módulo de validación humana.

El caso más importante: una sugerencia NO puede quedar confirmada sin que
una persona la revise. Es la regla que sostiene todo MapAid.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import config
from db import database
from modules.deteccion import models as deteccion_models
from modules.deteccion.schemas import SuggestionStatus
from modules.validacion.schemas import ValidationAction, ValidationRequest
from modules.validacion.services import AlreadyReviewed, SuggestionNotFound, validar
from modules.validacion.services import cola_de_revision, historial


@pytest.fixture(autouse=True)
def base_de_datos_temporal():
    """Base de datos aislada para cada prueba."""

    anterior = config.DATABASE_PATH
    with TemporaryDirectory() as carpeta:
        config.DATABASE_PATH = str(Path(carpeta) / "test.db")
        database.init_db()
        try:
            yield
        finally:
            config.DATABASE_PATH = anterior


def crear_sugerencia(**cambios) -> int:
    datos = {
        "escena": "palu-tsunami_00000124",
        "edificio_uid": "uid-de-prueba",
        "dano": "destroyed",
        "confianza": 0.8,
        "latitud": -0.9,
        "longitud": 119.8,
        "capturada_en": "2018-10-01",
    }
    datos.update(cambios)
    deteccion_models.guardar_sugerencias([datos])
    return deteccion_models.listar_sugerencias()[0]["id"]


def test_una_sugerencia_nace_pendiente():
    """La IA nunca crea nada ya validado."""

    crear_sugerencia()

    sugerencia = deteccion_models.listar_sugerencias()[0]

    assert sugerencia["estado"] == SuggestionStatus.PENDING.value


def test_confirmar_cambia_el_estado_y_deja_rastro():
    sugerencia_id = crear_sugerencia()

    resultado = validar(
        sugerencia_id,
        ValidationRequest(accion=ValidationAction.CONFIRM, revisada_por="elena"),
    )

    assert resultado["estado"] == SuggestionStatus.CONFIRMED.value

    registro = historial(sugerencia_id)
    assert len(registro) == 1
    assert registro[0]["revisada_por"] == "elena"
    assert registro[0]["estado_anterior"] == SuggestionStatus.PENDING.value


def test_rechazar_exige_motivo():
    """Sin motivo no se puede estudiar después en qué falla la IA."""

    with pytest.raises(ValueError):
        ValidationRequest(accion=ValidationAction.REJECT, motivo="")


def test_corregir_exige_el_nivel_corregido():
    with pytest.raises(ValueError):
        ValidationRequest(accion=ValidationAction.CORRECT, motivo="se ve intacto")


def test_corregir_actualiza_el_nivel_de_dano():
    sugerencia_id = crear_sugerencia(dano="destroyed")

    resultado = validar(
        sugerencia_id,
        ValidationRequest(
            accion=ValidationAction.CORRECT,
            motivo="el tejado sigue en pie",
            dano_corregido="minor-damage",
        ),
    )

    assert resultado["estado"] == SuggestionStatus.CORRECTED.value
    assert resultado["dano"] == "minor-damage"


def test_no_se_puede_revisar_dos_veces():
    """La decisión de una persona no se sobrescribe en silencio."""

    sugerencia_id = crear_sugerencia()
    validar(sugerencia_id, ValidationRequest(accion=ValidationAction.CONFIRM))

    with pytest.raises(AlreadyReviewed):
        validar(sugerencia_id, ValidationRequest(accion=ValidationAction.CONFIRM))


def test_validar_algo_inexistente_avisa():
    with pytest.raises(SuggestionNotFound):
        validar(9999, ValidationRequest(accion=ValidationAction.CONFIRM))


def test_la_cola_solo_muestra_pendientes():
    primera = crear_sugerencia(edificio_uid="uid-1")
    crear_sugerencia(edificio_uid="uid-2")

    validar(primera, ValidationRequest(accion=ValidationAction.CONFIRM))

    pendientes = cola_de_revision()

    assert len(pendientes) == 1
    assert pendientes[0]["edificio_uid"] == "uid-2"


def test_reanalizar_no_borra_el_trabajo_ya_validado():
    """Volver a analizar una escena no debe pisar decisiones humanas."""

    sugerencia_id = crear_sugerencia()
    validar(sugerencia_id, ValidationRequest(accion=ValidationAction.CONFIRM))

    crear_sugerencia()  # mismo escena+uid: debe ignorarse

    sugerencias = deteccion_models.listar_sugerencias()
    assert len(sugerencias) == 1
    assert sugerencias[0]["estado"] == SuggestionStatus.CONFIRMED.value
