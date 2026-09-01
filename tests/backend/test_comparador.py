"""Pruebas del comparador de imágenes (la parte de IA).

Se usan imágenes sintéticas en vez de las de xBD: así los tests corren en
CI sin depender de que el dataset esté descargado.
"""
import numpy as np
import pytest
from PIL import Image

from modules.deteccion.comparador import (
    comparar_edificio,
    parse_wkt_polygon,
    polygon_bbox,
    polygon_centroid,
)
from modules.deteccion.schemas import DamageLevel

CUADRADO = "POLYGON ((10 10, 40 10, 40 40, 10 40, 10 10))"


def imagen_lisa(valor: int, tam: int = 64) -> Image.Image:
    return Image.fromarray(np.full((tam, tam, 3), valor, dtype=np.uint8))


def imagen_ruidosa(tam: int = 64) -> Image.Image:
    generador = np.random.default_rng(seed=7)
    datos = generador.integers(0, 255, size=(tam, tam, 3), dtype=np.uint8)
    return Image.fromarray(datos)


def test_parse_wkt_devuelve_los_vertices():
    puntos = parse_wkt_polygon(CUADRADO)

    assert puntos[0] == (10.0, 10.0)
    assert (40.0, 40.0) in puntos


def test_parse_wkt_admite_coordenadas_negativas():
    """Las longitudes de xBD son negativas en América: no deben perderse."""

    puntos = parse_wkt_polygon("POLYGON ((-118.81 34.03, -118.80 34.03))")

    assert puntos[0][0] == pytest.approx(-118.81)
    assert puntos[0][1] == pytest.approx(34.03)


def test_centroide_es_el_punto_medio():
    assert polygon_centroid([(0, 0), (10, 0), (10, 10), (0, 10)]) == (5.0, 5.0)


def test_bbox_se_recorta_a_los_limites_de_la_imagen():
    caja = polygon_bbox([(-5, -5), (200, 200)], ancho=64, alto=64)

    assert caja == (0, 0, 64, 64)


def test_bbox_descarta_poligonos_diminutos():
    """Un polígono de menos de 2 px no se puede comparar de forma fiable."""

    assert polygon_bbox([(10, 10), (10.5, 10.5)], ancho=64, alto=64) is None


def test_sin_cambios_no_reporta_dano():
    imagen = imagen_lisa(120)

    nivel, confianza = comparar_edificio(imagen, imagen, parse_wkt_polygon(CUADRADO))

    assert nivel == DamageLevel.NO_DAMAGE
    assert 0.0 <= confianza <= 1.0


def test_un_cambio_drastico_de_brillo_reporta_dano():
    antes = imagen_lisa(30)
    despues = imagen_lisa(230)

    nivel, _ = comparar_edificio(antes, despues, parse_wkt_polygon(CUADRADO))

    assert nivel == DamageLevel.DESTROYED


def test_un_cambio_de_textura_tambien_se_detecta():
    """Escombros: el brillo medio apenas cambia, la textura mucho."""

    antes = imagen_lisa(128)
    despues = imagen_ruidosa()

    nivel, _ = comparar_edificio(antes, despues, parse_wkt_polygon(CUADRADO))

    assert nivel != DamageLevel.NO_DAMAGE


def test_poligono_fuera_de_la_imagen_no_se_clasifica():
    imagen = imagen_lisa(120)

    nivel, confianza = comparar_edificio(
        imagen, imagen, parse_wkt_polygon("POLYGON ((500 500, 501 501))")
    )

    assert nivel == DamageLevel.UNCLASSIFIED
    assert confianza == 0.0


def test_la_confianza_nunca_llega_a_la_certeza_absoluta():
    """El método no puede estar seguro del todo, y no debe aparentarlo."""

    antes = imagen_lisa(0)
    despues = imagen_lisa(255)

    _, confianza = comparar_edificio(antes, despues, parse_wkt_polygon(CUADRADO))

    assert confianza < 1.0
