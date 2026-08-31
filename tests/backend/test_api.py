"""Pruebas de la API completa (detección + validación).

Se usan datos insertados a mano en vez de analizar imágenes reales: así
los tests corren en CI aunque data/raw/xbd esté vacío.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

import config
from db import database


@pytest.fixture
def cliente():
    """App con una base de datos temporal, limpia en cada prueba."""

    anterior = config.DATABASE_PATH
    with TemporaryDirectory() as carpeta:
        config.DATABASE_PATH = str(Path(carpeta) / "test.db")
        database.init_db()

        import main

        with TestClient(main.app) as cliente_http:
            yield cliente_http

        config.DATABASE_PATH = anterior


def insertar_sugerencia(uid="uid-1", dano="destroyed"):
    from modules.deteccion.models import guardar_sugerencias, listar_sugerencias

    guardar_sugerencias(
        [
            {
                "escena": "palu-tsunami_00000124",
                "edificio_uid": uid,
                "dano": dano,
                "confianza": 0.8,
                "latitud": -0.86,
                "longitud": 119.88,
                "capturada_en": "2018-10-01",
            }
        ]
    )
    return listar_sugerencias()[-1]["id"]


def test_health(cliente):
    assert cliente.get("/api/health").json() == {"status": "ok"}


def test_analizar_escena_inexistente_devuelve_404(cliente):
    respuesta = cliente.post("/api/deteccion/analizar", json={"escena": "no-existe"})

    assert respuesta.status_code == 404
    assert "error" in respuesta.json()


def test_la_respuesta_incluye_la_etiqueta_en_espanol(cliente):
    """El frontend pinta la etiqueta directamente, sin traducir nada."""

    insertar_sugerencia(dano="major-damage")

    sugerencia = cliente.get("/api/deteccion/sugerencias").json()[0]

    assert sugerencia["dano"] == "major-damage"
    assert sugerencia["dano_etiqueta"] == "Daño mayor"


def test_las_sugerencias_nacen_pendientes(cliente):
    insertar_sugerencia()

    assert cliente.get("/api/deteccion/sugerencias").json()[0]["estado"] == "pendiente"


def test_filtrar_sugerencias_por_estado(cliente):
    identificador = insertar_sugerencia(uid="uid-a")
    insertar_sugerencia(uid="uid-b")
    cliente.patch(f"/api/validacion/{identificador}", json={"accion": "confirmar"})

    pendientes = cliente.get("/api/deteccion/sugerencias?estado=pendiente").json()
    confirmadas = cliente.get("/api/deteccion/sugerencias?estado=confirmada").json()

    assert len(pendientes) == 1
    assert len(confirmadas) == 1


def test_confirmar_una_sugerencia(cliente):
    identificador = insertar_sugerencia()

    respuesta = cliente.patch(
        f"/api/validacion/{identificador}",
        json={"accion": "confirmar", "revisada_por": "elena"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "confirmada"


def test_no_se_puede_confirmar_dos_veces(cliente):
    identificador = insertar_sugerencia()
    cliente.patch(f"/api/validacion/{identificador}", json={"accion": "confirmar"})

    respuesta = cliente.patch(
        f"/api/validacion/{identificador}", json={"accion": "confirmar"}
    )

    assert respuesta.status_code == 409


def test_rechazar_sin_motivo_se_rechaza(cliente):
    identificador = insertar_sugerencia()

    respuesta = cliente.patch(
        f"/api/validacion/{identificador}", json={"accion": "rechazar"}
    )

    assert respuesta.status_code == 422


def test_validar_algo_inexistente_devuelve_404(cliente):
    respuesta = cliente.patch("/api/validacion/99999", json={"accion": "confirmar"})

    assert respuesta.status_code == 404


def test_el_historial_registra_quien_valido(cliente):
    identificador = insertar_sugerencia()
    cliente.patch(
        f"/api/validacion/{identificador}",
        json={"accion": "rechazar", "motivo": "es una sombra", "revisada_por": "gema"},
    )

    historial = cliente.get(f"/api/validacion/{identificador}/historial").json()

    assert len(historial) == 1
    assert historial[0]["revisada_por"] == "gema"
    assert historial[0]["motivo"] == "es una sombra"


def test_el_resumen_cuenta_por_estado(cliente):
    identificador = insertar_sugerencia(uid="uid-a")
    insertar_sugerencia(uid="uid-b")
    cliente.patch(f"/api/validacion/{identificador}", json={"accion": "confirmar"})

    resumen = cliente.get("/api/deteccion/resumen").json()

    assert resumen["pendiente"] == 1
    assert resumen["confirmada"] == 1
