from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.gis.geos import LinearRing, MultiPolygon, Polygon

from catalog.enums import SRID_WGS84, TipoCamion
from catalog.models import Zona
from shared.permisos import PermisoCodigo
from transportista.enums import ModalidadFlete
from transportista.models import TarifaFlete, Tarifario, Transportista

pytestmark = pytest.mark.django_db

ZONAS = "/api/v1/zonas/"

CUADRADO = [
    [
        [
            [-58.5, -34.6],
            [-58.4, -34.6],
            [-58.4, -34.5],
            [-58.5, -34.5],
            [-58.5, -34.6],
        ]
    ]
]

MONA = [
    [
        [
            [-58.5, -34.6],
            [-58.4, -34.5],
            [-58.4, -34.6],
            [-58.5, -34.5],
            [-58.5, -34.6],
        ]
    ]
]

# Dos cuadrados que no se tocan: lo que el PolygonField no podía guardar.
DISJUNTOS = [
    CUADRADO[0],
    [
        [
            [-60.5, -32.6],
            [-60.4, -32.6],
            [-60.4, -32.5],
            [-60.5, -32.5],
            [-60.5, -32.6],
        ]
    ],
]


def zona_in(nombre: str, coordinates: list) -> dict:
    return {"nombre": nombre, "geom": {"type": "MultiPolygon", "coordinates": coordinates}}


def multipolygon(coordinates: list) -> MultiPolygon:
    poligonos = [
        Polygon(*[LinearRing([tuple(punto) for punto in anillo]) for anillo in poligono])
        for poligono in coordinates
    ]
    return MultiPolygon(*poligonos, srid=SRID_WGS84)


@pytest.fixture
def usuario_con(crear_usuario, crear_rol, asignar_rol):
    def _crear(*codigos: PermisoCodigo):
        user = crear_usuario()
        asignar_rol(user, crear_rol("rol", *codigos))
        return user

    return _crear


def test_crear_devuelve_el_anillo_cerrado(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(ZONAS, zona_in("Norte", CUADRADO), content_type="application/json")

    assert resp.status_code == 201
    anillo = resp.json()["geom"]["coordinates"][0][0]
    assert anillo[0] == anillo[-1]


def test_una_zona_puede_ser_dos_poligonos_disjuntos(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(ZONAS, zona_in("Dos islas", DISJUNTOS), content_type="application/json")

    assert resp.status_code == 201
    assert len(resp.json()["geom"]["coordinates"]) == 2


def test_un_polygon_pelado_se_rechaza_con_payload_invalid(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))
    payload = {"nombre": "Norte", "geom": {"type": "Polygon", "coordinates": CUADRADO[0]}}

    resp = client.post(ZONAS, payload, content_type="application/json")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_polygon_que_se_autointersecta_da_business_rule(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(ZONAS, zona_in("Moña", MONA), content_type="application/json")

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "business_rule"
    assert body["error"]["detail"]["motivo"]


def test_nombre_vacio_da_payload_invalid_y_no_business_rule(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))

    resp = client.post(ZONAS, zona_in("", CUADRADO), content_type="application/json")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_nombre_duplicado_da_conflict(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR))
    client.post(ZONAS, zona_in("Norte", CUADRADO), content_type="application/json")

    resp = client.post(ZONAS, zona_in("Norte", CUADRADO), content_type="application/json")

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "conflict"
    assert body["error"]["detail"]["nombre"] == "Norte"


def test_eliminar_da_de_baja_logica(client, usuario_con):
    user = usuario_con(PermisoCodigo.ZONAS_VER, PermisoCodigo.ZONAS_ELIMINAR)
    client.force_login(user)
    zona = Zona.objects.create(nombre="Norte", geom=multipolygon(CUADRADO))

    resp = client.delete(f"{ZONAS}{zona.id}")

    assert resp.status_code == 204
    assert client.get(ZONAS).json() == []
    assert Zona.all_objects.filter(pk=zona.id, active=False).exists()


def test_el_nombre_queda_libre_despues_de_eliminar(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_CREAR, PermisoCodigo.ZONAS_ELIMINAR))
    creada = client.post(ZONAS, zona_in("Norte", CUADRADO), content_type="application/json")
    client.delete(f"{ZONAS}{creada.json()['id']}")

    resp = client.post(ZONAS, zona_in("Norte", CUADRADO), content_type="application/json")

    assert resp.status_code == 201


def test_eliminar_una_zona_con_tarifas_da_conflict_y_no_500(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_ELIMINAR))
    zona = Zona.objects.create(nombre="Norte", geom=multipolygon(CUADRADO))
    tarifario = Tarifario.objects.create(
        transportista=Transportista.objects.create(cuit="30-11111111-9", razon_social="Fletes SA"),
        vigente_desde=datetime(2026, 1, 1, tzinfo=UTC),
    )
    TarifaFlete.objects.create(
        tarifario=tarifario,
        zona=zona,
        modalidad=ModalidadFlete.DIRECTO.value,
        tipo_camion=TipoCamion.SEMI.value,
        precio=Decimal("185000.00"),
    )

    resp = client.delete(f"{ZONAS}{zona.id}")

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "conflict"
    assert body["error"]["detail"]["tarifas_flete"] == 1
    assert Zona.objects.filter(pk=zona.id).exists()


def test_eliminar_una_zona_inexistente_da_404(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_ELIMINAR))

    resp = client.delete(f"{ZONAS}9999")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_eliminar_sin_permiso_da_403_y_no_401(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ZONAS_VER))
    zona = Zona.objects.create(nombre="Norte", geom=multipolygon(CUADRADO))

    resp = client.delete(f"{ZONAS}{zona.id}")

    assert resp.status_code == 403
    assert resp.json()["error"]["detail"]["requiere"] == [PermisoCodigo.ZONAS_ELIMINAR.value]
