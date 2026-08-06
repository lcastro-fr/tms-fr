from __future__ import annotations

import pytest

from catalog.models import Ubicacion
from catalog.services import UbicacionService

pytestmark = pytest.mark.django_db

def upsert(
    codigo: str,
    validada: bool,
    nombre: str = "Cliente Uno",
    lat: float | None = None,
    lng: float | None = None,
):
    return UbicacionService.upsert_by_codigo(
        codigo=codigo,
        tipo="cliente",
        nombre=nombre,
        calle="Av. Corrientes 1000",
        localidad="CABA",
        provincia="Buenos Aires",
        lat=lat,
        lng=lng,
        validada=validada,
    )


def test_el_upsert_es_idempotente_por_codigo_aunque_cambie_validada():
    upsert("CL100", validada=True)

    ubicacion, creada = upsert("CL100", validada=False, nombre="Cliente Uno Corregido")

    assert creada is False
    assert ubicacion.nombre == "Cliente Uno Corregido"
    assert Ubicacion.objects.filter(codigo="CL100").count() == 1


def test_el_upsert_no_desvalida_una_ubicacion_ya_corregida():
    upsert("CL100", validada=False)
    Ubicacion.objects.filter(codigo="CL100").update(validada=True)

    upsert("CL100", validada=False)

    assert Ubicacion.objects.get(codigo="CL100").validada is True


def test_el_upsert_fija_validada_al_crear():
    ubicacion, creada = upsert("CL200", validada=False)

    assert creada is True
    assert ubicacion.validada is False


def test_un_upsert_sin_coordenadas_no_borra_la_que_ya_estaba():
    upsert("CL100", validada=False)
    UbicacionService.update_ubicacion(
        Ubicacion.objects.get(codigo="CL100"), nombre="Corregida", tipo="cliente",
        lat=-34.6037, lng=-58.3816,
    )

    upsert("CL100", validada=False, lat=None, lng=None)

    ubicacion = Ubicacion.objects.get(codigo="CL100")
    assert ubicacion.coordinates is not None
    assert ubicacion.validada is True


def test_un_upsert_con_coordenadas_si_actualiza_la_anterior():
    upsert("CL100", validada=True, lat=-30.0, lng=-60.0)

    upsert("CL100", validada=True, lat=-34.6037, lng=-58.3816)

    ubicacion = Ubicacion.objects.get(codigo="CL100")
    assert ubicacion.coordinates is not None
    assert (ubicacion.coordinates.x, ubicacion.coordinates.y) == pytest.approx(
        (-58.3816, -34.6037)
    )
