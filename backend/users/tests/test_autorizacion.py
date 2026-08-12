from __future__ import annotations

import pytest

from shared.permisos import PermisoCodigo

pytestmark = pytest.mark.django_db

ZONAS = "/api/v1/zonas/"

ZONA_IN = {
    "nombre": "Norte",
    "geom": {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [-58.5, -34.6],
                    [-58.4, -34.6],
                    [-58.4, -34.5],
                    [-58.5, -34.5],
                    [-58.5, -34.6],
                ]
            ]
        ],
    },
}


def test_sin_sesion_da_401(client, permisos):
    assert client.get(ZONAS).status_code == 401


def test_la_api_key_de_ingesta_ya_no_sirve_para_zonas(client, permisos, settings):
    settings.INGEST_API_KEY = "una-key"

    resp = client.get(ZONAS, HTTP_X_API_KEY="una-key")

    assert resp.status_code == 401


def test_logueado_sin_permiso_da_403_y_no_401(client, crear_usuario, permisos):
    """Un 401 acá desloguearía al usuario en el frontend. Tiene que ser 403."""
    client.force_login(crear_usuario())

    resp = client.post(ZONAS, ZONA_IN, content_type="application/json")

    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "forbidden"
    assert body["error"]["detail"]["requiere"] == [PermisoCodigo.ZONAS_CREAR.value]


def test_con_permiso_de_lectura_puede_listar(client, crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))
    client.force_login(user)

    resp = client.get(ZONAS)

    assert resp.status_code == 200
    assert resp.json() == []


def test_permiso_de_lectura_no_alcanza_para_crear(client, crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))
    client.force_login(user)

    resp = client.post(ZONAS, ZONA_IN, content_type="application/json")

    assert resp.status_code == 403


def test_con_permiso_de_creacion_crea(client, crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("alta", PermisoCodigo.ZONAS_CREAR))
    client.force_login(user)

    resp = client.post(ZONAS, ZONA_IN, content_type="application/json")

    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Norte"


def test_superuser_pasa_sin_roles(client, crear_usuario, permisos):
    client.force_login(crear_usuario(email="admin@tms.test", is_staff=True, is_superuser=True))

    assert client.get(ZONAS).status_code == 200
