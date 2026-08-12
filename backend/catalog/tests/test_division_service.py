from __future__ import annotations

import math
from decimal import Decimal

import pytest
from django.contrib.gis.geos import LinearRing, MultiPolygon, Polygon

from catalog.enums import SRID_WGS84
from catalog.models import Departamento, Provincia
from catalog.services import DivisionService

pytestmark = pytest.mark.django_db


def circulo(centro_x: float, centro_y: float, radio: float, lados: int) -> MultiPolygon:
    """Un polígono de muchos vértices: es lo que la simplificación tiene que poder bajar."""
    puntos = [
        (
            centro_x + radio * math.cos(2 * math.pi * i / lados),
            centro_y + radio * math.sin(2 * math.pi * i / lados),
        )
        for i in range(lados)
    ]
    return MultiPolygon(Polygon(LinearRing([*puntos, puntos[0]])), srid=SRID_WGS84)


@pytest.fixture
def provincia_circular(db):
    geom = circulo(-60.0, -33.0, 1.0, 2000)
    return Provincia.objects.create(
        codigo="82",
        nombre="Santa Fe",
        superficie_km2=Decimal("1.0000"),
        geom=geom,
        geom_display=geom,
    )


def test_la_union_de_un_solo_poligono_igual_sale_multipolygon(provincia_circular):
    geom, _ = DivisionService.union_de(["82"], [])

    assert geom.geom_type == "MultiPolygon"
    assert geom.num_geom == 1
    assert geom.srid == SRID_WGS84


def test_simplificar_baja_los_vertices_sin_invalidar(provincia_circular):
    geom, _ = DivisionService.union_de(["82"], [])

    assert geom.num_points < provincia_circular.geom.num_points / 10
    assert geom.valid, geom.valid_reason


def test_la_union_no_toca_geom_display(provincia_circular):
    """geom_display es de dibujo: si la unión saliera de ahí, la zona perdería el borde."""
    grueso = circulo(-60.0, -33.0, 1.0, 8)
    Provincia.objects.filter(codigo="82").update(geom_display=grueso)

    geom, _ = DivisionService.union_de(["82"], [])

    assert geom.num_points > grueso.num_points


def test_un_codigo_de_provincia_no_matchea_un_departamento(provincia_circular):
    Departamento.objects.create(
        codigo="82084",
        provincia=provincia_circular,
        nombre="Rosario",
        superficie_km2=Decimal("1.0000"),
        geom=circulo(-60.0, -33.0, 0.5, 8),
        geom_display=circulo(-60.0, -33.0, 0.5, 8),
    )

    with pytest.raises(DivisionService.DivisionNoEncontradaError) as exc:
        DivisionService.union_de(["82084"], [])

    assert exc.value.detail["codigos"] == ["82084"]
