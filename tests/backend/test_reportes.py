"""Pruebas de los reportes hechos por personas sobre el terreno.

Cubre lo que la IA no puede aportar: daños que se le escaparon, recursos
disponibles y accesos bloqueados.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import config
from db import database
from modules.deteccion.schemas import SuggestionStatus
from modules.reportes.schemas import LocalReportRequest
from modules.reportes.services import contar_por_origen, crear_reporte, listar_reportes


@pytest.fixture(autouse=True)
def base_de_datos_temporal():
    anterior = config.DATABASE_PATH
    with TemporaryDirectory() as carpeta:
        config.DATABASE_PATH = str(Path(carpeta) / "test.db")
        database.init_db()
        try:
            yield
        finally:
            config.DATABASE_PATH = anterior


def peticion(**cambios) -> LocalReportRequest:
    datos = {
        "escena": "palu-tsunami_00000124",
        "categoria": "dano",
        "dano": "destroyed",
        "latitud": -0.862,
        "longitud": 119.88,
        "descripcion": "La casa de la esquina se cayó entera",
        "reportado_por": "vecina de Palu",
    }
    datos.update(cambios)
    return LocalReportRequest(**datos)


def test_un_reporte_local_nace_pendiente():
    """Todos los reportes pasan por la administradora antes de publicarse."""

    reporte = crear_reporte(peticion())

    assert reporte["estado"] == SuggestionStatus.PENDING.value
    assert reporte["origen"] == "persona"


def test_un_reporte_local_tiene_confianza_maxima():
    """No es una estimación como la de la IA: es un testimonio directo."""

    assert crear_reporte(peticion())["confianza"] == 1.0


def test_se_guarda_quien_lo_reporto():
    """Hace falta para poder contrastarlo si algo no cuadra."""

    reporte = crear_reporte(peticion(reportado_por="Ibu Sari"))

    assert reporte["reportado_por"] == "Ibu Sari"


def test_se_puede_reportar_un_recurso_disponible():
    """Un pozo que funciona no se ve en una imagen de satélite."""

    reporte = crear_reporte(
        peticion(categoria="recurso", dano=None, descripcion="Pozo con agua potable")
    )

    assert reporte["categoria"] == "recurso"
    # Un recurso no tiene nivel de daño: no se inventa uno.
    assert reporte["dano"] == "un-classified"


def test_se_puede_reportar_un_acceso_bloqueado():
    reporte = crear_reporte(
        peticion(categoria="acceso", dano=None, descripcion="Puente cortado")
    )

    assert reporte["categoria"] == "acceso"


def test_reportar_un_dano_exige_indicar_su_nivel():
    with pytest.raises(ValueError):
        peticion(dano=None)


def test_un_recurso_no_admite_nivel_de_dano():
    """Evita datos incoherentes: un pozo no está 'destruido'."""

    with pytest.raises(ValueError):
        peticion(categoria="recurso", dano="destroyed")


def test_la_descripcion_es_obligatoria():
    """Sin descripción, un punto en el mapa no dice nada útil."""

    with pytest.raises(ValueError):
        peticion(descripcion="")


def test_dos_personas_pueden_reportar_en_el_mismo_punto():
    """No hay restricción de unicidad: dos vecinos ven cosas distintas."""

    crear_reporte(peticion(descripcion="Se cayó el tejado"))
    crear_reporte(peticion(descripcion="Además hay una fuga de gas"))

    assert len(listar_reportes()) == 2


def test_filtrar_reportes_por_categoria():
    crear_reporte(peticion())
    crear_reporte(peticion(categoria="recurso", dano=None, descripcion="Pozo"))

    assert len(listar_reportes(categoria="recurso")) == 1
    assert len(listar_reportes(categoria="dano")) == 1


def test_el_recuento_separa_ia_de_personas():
    """Es el dato que enseña que las dos fuentes se complementan."""

    from modules.deteccion.models import guardar_sugerencias

    guardar_sugerencias(
        [
            {
                "escena": "palu-tsunami_00000124",
                "edificio_uid": "uid-ia",
                "dano": "destroyed",
                "confianza": 0.8,
                "latitud": -0.86,
                "longitud": 119.88,
            }
        ]
    )
    crear_reporte(peticion())

    assert contar_por_origen() == {"ia": 1, "persona": 1}


def test_los_reportes_locales_entran_en_la_cola_de_revision():
    """Todos los reportes de personas esperan revisión de la administradora."""

    from modules.validacion.services import cola_de_revision

    crear_reporte(peticion())

    sugerencias_pendientes = cola_de_revision()
    assert len(sugerencias_pendientes) == 1
    assert sugerencias_pendientes[0]["estado"] == "pendiente"
    assert sugerencias_pendientes[0]["origen"] == "persona"


def test_se_puede_validar_un_reporte_local():
    """La administradora puede confirmar un reporte local pendiente."""

    from modules.validacion.schemas import ValidationAction, ValidationRequest
    from modules.validacion.services import validar

    reporte = crear_reporte(peticion())

    validado = validar(
        reporte["id"], ValidationRequest(accion=ValidationAction.CONFIRM)
    )

    assert validado["estado"] == "confirmada"
    assert validado["origen"] == "persona"
