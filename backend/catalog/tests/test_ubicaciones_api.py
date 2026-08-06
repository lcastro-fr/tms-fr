from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point

from catalog.enums import SRID_WGS84
from catalog.models import Ubicacion
from shared.permisos import PermisoCodigo

pytestmark = pytest.mark.django_db

UBICACIONES = "/api/v1/ubicaciones/"


@pytest.fixture
def crear_ubicacion(db):
    def _crear(nombre: str, codigo: str, coordinates: Point | None = None) -> Ubicacion:
        return Ubicacion.objects.create(
            nombre=nombre,
            codigo=codigo,
            calle="Av. Siempre Viva 742",
            localidad="Rosario",
            provincia="Santa Fe",
            coordinates=coordinates,
        )

    return _crear


@pytest.fixture
def lector(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.UBICACIONES_VER))
    return user


def test_sin_sesion_da_401(client, permisos):
    assert client.get(UBICACIONES).status_code == 401


def test_logueado_sin_permiso_da_403_y_no_401(client, crear_usuario, permisos):
    client.force_login(crear_usuario())

    resp = client.get(UBICACIONES)

    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "forbidden"
    assert body["error"]["detail"]["requiere"] == [PermisoCodigo.UBICACIONES_VER.value]


def test_las_coordenadas_salen_en_orden_geojson(client, lector, crear_ubicacion):
    crear_ubicacion("Planta Rosario", "PL01", Point(-60.6393, -32.9468, srid=SRID_WGS84))
    client.force_login(lector)

    resp = client.get(UBICACIONES)

    assert resp.status_code == 200
    punto = resp.json()[0]["coordinates"]
    assert punto["type"] == "Point"
    lng, lat = punto["coordinates"]
    assert (lng, lat) == pytest.approx((-60.6393, -32.9468))


def test_una_ubicacion_sin_punto_viaja_con_coordinates_en_null(client, lector, crear_ubicacion):
    """El frontend cuenta estas para avisarle al usuario que no se dibujan."""
    crear_ubicacion("Cliente sin geo", "CL100")
    client.force_login(lector)

    resp = client.get(UBICACIONES)

    assert resp.json()[0]["coordinates"] is None


def test_no_lista_las_dadas_de_baja(client, lector, crear_ubicacion):
    crear_ubicacion("Viva", "CL100")
    crear_ubicacion("Muerta", "CL200").delete()
    client.force_login(lector)

    nombres = [u["nombre"] for u in client.get(UBICACIONES).json()]

    assert nombres == ["Viva"]
