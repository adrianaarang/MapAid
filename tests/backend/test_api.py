"""Pruebas de la API completa (detección + validación + auth)."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

import config
from db import database


@pytest.fixture
def cliente():
    anterior = config.DATABASE_PATH
    with TemporaryDirectory() as carpeta:
        config.DATABASE_PATH = str(Path(carpeta) / "test.db")
        database.init_db()
        import main
        with TestClient(main.app) as c:
            yield c
        config.DATABASE_PATH = anterior


def token_admin(cliente):
    r = cliente.post("/api/auth/login",
        json={"email": "admin@mapaid.com", "contrasena": "admin1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def token_coop(cliente):
    r = cliente.post("/api/auth/login",
        json={"email": "cooperante@mapaid.com", "contrasena": "cooperante1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def insertar(cliente, uid="uid-1", dano="destroyed"):
    from modules.deteccion.models import guardar_sugerencias, listar_sugerencias
    guardar_sugerencias([{"escena": "test", "edificio_uid": uid, "dano": dano,
        "confianza": 0.8, "latitud": -0.86, "longitud": 119.88, "capturada_en": "2018-10-01"}])
    return listar_sugerencias()[-1]["id"]


def test_health(cliente):
    assert cliente.get("/api/health").json() == {"status": "ok"}


def test_login_admin_correcto(cliente):
    r = cliente.post("/api/auth/login",
        json={"email": "admin@mapaid.com", "contrasena": "admin1234"})
    assert r.status_code == 200
    assert r.json()["rol"] == "administradora"


def test_login_cooperante_correcto(cliente):
    r = cliente.post("/api/auth/login",
        json={"email": "cooperante@mapaid.com", "contrasena": "cooperante1234"})
    assert r.status_code == 200
    assert r.json()["rol"] == "cooperante"


def test_login_contrasena_incorrecta(cliente):
    r = cliente.post("/api/auth/login",
        json={"email": "admin@mapaid.com", "contrasena": "incorrecta"})
    assert r.status_code == 401


def test_cooperante_no_puede_validar(cliente):
    sid = insertar(cliente)
    r = cliente.patch(f"/api/validacion/{sid}",
        json={"accion": "confirmar"},
        headers=token_coop(cliente))
    assert r.status_code == 403


def test_sin_token_no_puede_validar(cliente):
    sid = insertar(cliente)
    r = cliente.patch(f"/api/validacion/{sid}", json={"accion": "confirmar"})
    assert r.status_code in (401, 403)  # sin token: 401 Unauthorized


def test_analizar_escena_inexistente_devuelve_404(cliente):
    r = cliente.post("/api/deteccion/analizar",
        json={"escena": "no-existe"},
        headers=token_admin(cliente))
    assert r.status_code == 404


def test_las_sugerencias_nacen_pendientes(cliente):
    insertar(cliente)
    r = cliente.get("/api/deteccion/sugerencias", headers=token_admin(cliente))
    assert r.json()[0]["estado"] == "pendiente"


def test_confirmar_una_sugerencia(cliente):
    sid = insertar(cliente)
    r = cliente.patch(f"/api/validacion/{sid}",
        json={"accion": "confirmar", "revisada_por": "elena"},
        headers=token_admin(cliente))
    assert r.status_code == 200
    assert r.json()["estado"] == "confirmada"


def test_no_se_puede_confirmar_dos_veces(cliente):
    sid = insertar(cliente)
    cabecera = token_admin(cliente)
    cliente.patch(f"/api/validacion/{sid}", json={"accion": "confirmar"}, headers=cabecera)
    r = cliente.patch(f"/api/validacion/{sid}", json={"accion": "confirmar"}, headers=cabecera)
    assert r.status_code == 409


def test_rechazar_sin_motivo_devuelve_422(cliente):
    sid = insertar(cliente)
    r = cliente.patch(f"/api/validacion/{sid}",
        json={"accion": "rechazar"},
        headers=token_admin(cliente))
    assert r.status_code == 422


def test_el_historial_registra_quien_valido(cliente):
    sid = insertar(cliente)
    cliente.patch(f"/api/validacion/{sid}",
        json={"accion": "rechazar", "motivo": "es una sombra", "revisada_por": "gema"},
        headers=token_admin(cliente))
    h = cliente.get(f"/api/validacion/{sid}/historial", headers=token_admin(cliente)).json()
    assert h[0]["revisada_por"] == "gema"
    assert h[0]["motivo"] == "es una sombra"


def test_el_resumen_cuenta_por_estado(cliente):
    sid_a = insertar(cliente, uid="a")
    insertar(cliente, uid="b")
    cliente.patch(f"/api/validacion/{sid_a}",
        json={"accion": "confirmar"},
        headers=token_admin(cliente))
    r = cliente.get("/api/deteccion/resumen", headers=token_admin(cliente)).json()
    assert r["pendiente"] == 1
    assert r["confirmada"] == 1
