from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.gis.geos import LinearRing, MultiPolygon, Polygon

from catalog.enums import SRID_WGS84
from catalog.models import Departamento, Provincia
from shared.permisos import PermisoCodigo

pytestmark = pytest.mark.django_db

PROVINCIAS = "/api/v1/divisiones/provincias"
UNION = "/api/v1/divisiones/union"


def cuadrado(x: float, y: float, lado: float = 1.0) -> MultiPolygon:
    anillo = LinearRing(
        [(x, y), (x + lado, y), (x + lado, y + lado), (x, y + lado), (x, y)],
    )
    return MultiPolygon(Polygon(anillo), srid=SRID_WGS84)


@pytest.fixture
def usuario_con(crear_usuario, crear_rol, asignar_rol):
    def _crear(*codigos: PermisoCodigo):
        user = crear_usuario()
        asignar_rol(user, crear_rol("rol", *codigos))
        return user

    return _crear


@pytest.fixture
def santa_fe(db):
    provincia = Provincia.objects.create(
        codigo="82",
        nombre="Santa Fe",
        superficie_km2=Decimal("2.0000"),
        geom=cuadrado(-60.0, -33.0, 2.0),
        geom_display=cuadrado(-60.0, -33.0, 2.0),
    )
    # Dos departamentos que se tocan en x=-59: la unión tiene que dar un solo polígono.
    Departamento.objects.create(
        codigo="82084",
        provincia=provincia,
        nombre="Rosario",
        superficie_km2=Decimal("1.0000"),
        geom=cuadrado(-60.0, -33.0),
        geom_display=cuadrado(-60.0, -33.0),
    )
    Departamento.objects.create(
        codigo="82063",
        provincia=provincia,
        nombre="San Lorenzo",
        superficie_km2=Decimal("1.0000"),
        geom=cuadrado(-59.0, -33.0),
        geom_display=cuadrado(-59.0, -33.0),
    )
    return provincia


@pytest.fixture
def chubut(db):
    return Provincia.objects.create(
        codigo="26",
        nombre="Chubut",
        superficie_km2=Decimal("1.0000"),
        geom=cuadrado(-70.0, -44.0),
        geom_display=cuadrado(-70.0, -44.0),
    )


def test_la_lista_cuenta_los_departamentos(client, usuario_con, santa_fe, chubut):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))

    resp = client.get(PROVINCIAS)

    assert resp.status_code == 200
    por_codigo = {p["codigo"]: p for p in resp.json()}
    assert por_codigo["82"]["cantidad_departamentos"] == 2
    assert por_codigo["26"]["cantidad_departamentos"] == 0
    assert por_codigo["82"]["geom"]["type"] == "MultiPolygon"


def test_las_provincias_salen_por_nombre(client, usuario_con, santa_fe, chubut):
    """Django ignora Meta.ordering en cuanto la query agrupa: el order_by tiene que ser explícito."""
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))

    nombres = [p["nombre"] for p in client.get(PROVINCIAS).json()]

    assert nombres == sorted(nombres)
    assert nombres == ["Chubut", "Santa Fe"]


def test_un_departamento_dado_de_baja_no_se_cuenta(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))
    Departamento.objects.get(codigo="82084").delete()

    resp = client.get(PROVINCIAS)

    assert resp.json()[0]["cantidad_departamentos"] == 1


def test_los_departamentos_salen_por_provincia(client, usuario_con, santa_fe, chubut):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))

    resp = client.get(f"{PROVINCIAS}/82/departamentos")

    assert resp.status_code == 200
    assert sorted(d["codigo"] for d in resp.json()) == ["82063", "82084"]
    assert client.get(f"{PROVINCIAS}/26/departamentos").json() == []


def test_una_provincia_inexistente_da_404(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))

    resp = client.get(f"{PROVINCIAS}/99/departamentos")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_dos_departamentos_vecinos_dan_un_solo_poligono(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(
        UNION, {"departamentos": ["82084", "82063"]}, content_type="application/json"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["poligonos"] == 1
    assert body["geom"]["type"] == "MultiPolygon"
    assert len(body["geom"]["coordinates"]) == 1
    assert body["superficie_km2"] == "2.0000"


def test_dos_provincias_lejanas_dan_dos_poligonos(client, usuario_con, santa_fe, chubut):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(UNION, {"provincias": ["82", "26"]}, content_type="application/json")

    assert resp.status_code == 200
    assert resp.json()["poligonos"] == 2


def test_la_superficie_no_cuenta_dos_veces_un_departamento_de_una_provincia_marcada(
    client, usuario_con, santa_fe
):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(
        UNION,
        {"provincias": ["82"], "departamentos": ["82084"]},
        content_type="application/json",
    )

    assert resp.json()["superficie_km2"] == "2.0000"


def test_un_codigo_inexistente_da_business_rule_y_no_404(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(
        UNION, {"departamentos": ["82084", "99999"]}, content_type="application/json"
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "business_rule"
    assert body["error"]["detail"]["codigos"] == ["99999"]


def test_la_seleccion_vacia_da_payload_invalid(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(
        UNION, {"provincias": [], "departamentos": []}, content_type="application/json"
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_unir_con_solo_permiso_de_editar_alcanza(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_EDITAR))

    resp = client.post(UNION, {"departamentos": ["82084"]}, content_type="application/json")

    assert resp.status_code == 200


def test_unir_con_solo_permiso_de_ver_da_403(client, usuario_con, santa_fe):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))

    resp = client.post(UNION, {"departamentos": ["82084"]}, content_type="application/json")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_sin_sesion_da_401(client, santa_fe):
    assert client.get(PROVINCIAS).status_code == 401
    assert (
        client.post(UNION, {"provincias": ["82"]}, content_type="application/json").status_code
        == 401
    )
