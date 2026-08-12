from __future__ import annotations

import pytest
from django.contrib.gis.geos import LinearRing, MultiPolygon, Point, Polygon

from catalog.enums import SRID_WGS84
from catalog.models import Zona
from catalog.services import ZonaService

pytestmark = pytest.mark.django_db


def cuadrado(nombre: str, centro: tuple[float, float], lado: float) -> Zona:
    x, y = centro
    mitad = lado / 2
    anillo = LinearRing(
        [
            (x - mitad, y - mitad),
            (x + mitad, y - mitad),
            (x + mitad, y + mitad),
            (x - mitad, y + mitad),
            (x - mitad, y - mitad),
        ]
    )
    return Zona.objects.create(
        nombre=nombre, geom=MultiPolygon(Polygon(anillo), srid=SRID_WGS84)
    )


def test_las_zonas_que_cubren_los_puntos_vienen_de_la_mas_chica_a_la_mas_grande():
    centro = (-58.45, -34.55)
    cuadrado("Grande", centro, 1.0)
    cuadrado("Chica", centro, 0.1)
    cuadrado("Mediana", centro, 0.5)

    zonas = ZonaService.get_zones_covering_all([Point(*centro, srid=SRID_WGS84)])

    assert [z.nombre for z in zonas] == ["Chica", "Mediana", "Grande"]
