from __future__ import annotations

import pytest
from django.test import Client

from shared.permisos import PermisoCodigo

pytestmark = pytest.mark.django_db

CSRF = "/api/v1/auth/csrf"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def _login(client: Client, email: str, password: str, token: str | None = None):
    body = {"email": email, "password": password}
    if token is None:
        return client.post(LOGIN, body, content_type="application/json")
    return client.post(LOGIN, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)


def test_me_sin_sesion_da_401(client):
    resp = client.get(ME)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_login_devuelve_la_sesion_con_roles_y_permisos(
    client, crear_usuario, crear_rol, asignar_rol, password
):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))

    resp = _login(client, user.email, password)

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == user.email
    assert body["roles"] == ["lectura"]
    assert body["permisos"] == [PermisoCodigo.ZONAS_VER.value]
    assert body["csrf_token"]


def test_login_con_credenciales_invalidas_da_401(client, crear_usuario, permisos):
    user = crear_usuario()

    resp = _login(client, user.email, "incorrecta")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_me_devuelve_la_sesion_despues_del_login(client, crear_usuario, password, permisos):
    user = crear_usuario()
    _login(client, user.email, password)

    resp = client.get(ME)

    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


def test_logout_mata_la_sesion(client, crear_usuario, password, permisos):
    user = crear_usuario()
    _login(client, user.email, password)

    assert client.post(LOGOUT).status_code == 204
    assert client.get(ME).status_code == 401


def test_csrf_entrega_un_token(client):
    resp = client.get(CSRF)

    assert resp.status_code == 200
    assert resp.json()["csrf_token"]


class TestCsrf:
    """Con enforce_csrf_checks el client de Django deja de saltear el chequeo."""

    def test_login_sin_header_da_403_con_el_envelope(self, crear_usuario, password, permisos):
        user = crear_usuario()
        estricto = Client(enforce_csrf_checks=True)

        resp = _login(estricto, user.email, password)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "forbidden"

    def test_login_con_header_del_bootstrap_funciona(self, crear_usuario, password, permisos):
        user = crear_usuario()
        estricto = Client(enforce_csrf_checks=True)
        boot = estricto.get(CSRF).json()["csrf_token"]

        resp = _login(estricto, user.email, password, token=boot)

        assert resp.status_code == 200

    def test_el_token_del_bootstrap_muere_con_el_login(self, crear_usuario, password, permisos):
        """login() llama a rotate_token(): por eso la respuesta trae el nuevo."""
        user = crear_usuario()
        estricto = Client(enforce_csrf_checks=True)
        boot = estricto.get(CSRF).json()["csrf_token"]
        nuevo = _login(estricto, user.email, password, token=boot).json()["csrf_token"]

        viejo = estricto.post(LOGOUT, HTTP_X_CSRFTOKEN=boot)
        assert viejo.status_code == 403
        assert viejo.json()["error"]["code"] == "forbidden"

        assert estricto.post(LOGOUT, HTTP_X_CSRFTOKEN=nuevo).status_code == 204
