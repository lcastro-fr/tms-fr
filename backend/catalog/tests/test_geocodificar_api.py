from __future__ import annotations

import pytest

from catalog.models import Pais
from conftest import GeocoderFalso
from lib.routing.domain import Coordinate, RoutingError
from shared.permisos import PermisoCodigo

pytestmark = pytest.mark.django_db

GEOCODIFICAR = "/api/v1/ubicaciones/geocodificar"

BUENOS_AIRES = Coordinate.from_lnglat(-58.3816, -34.6037)


@pytest.fixture
def argentina(db):
    return Pais.objects.get_or_create(codigo="AR", defaults={"nombre": "Argentina"})[0]


@pytest.fixture
def usuario_con(crear_usuario, crear_rol, asignar_rol):
    def _crear(*codigos: PermisoCodigo):
        user = crear_usuario()
        asignar_rol(user, crear_rol("rol", *codigos))
        return user

    return _crear


@pytest.fixture
def falso(monkeypatch):
    """El endpoint arma su geocoder con build_geocoder: se pisa el nombre en catalog.api."""

    def _instalar(coordinate: Coordinate | None = None, error: RoutingError | None = None):
        instancia = GeocoderFalso(coordinate=coordinate, error=error)
        monkeypatch.setattr("catalog.api.build_geocoder", lambda: instancia)
        return instancia

    return _instalar


def payload(**extra) -> dict:
    cuerpo = {
        "calle": "Av. Corrientes 1000",
        "localidad": "CABA - Buenos Aires",
        "provincia": "Buenos Aires",
        "pais_codigo": "AR",
    }
    cuerpo.update(extra)
    return cuerpo


def test_devuelve_la_coordenada_y_lo_que_se_busco(client, usuario_con, argentina, falso):
    falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(GEOCODIFICAR, payload(), content_type="application/json")

    assert resp.status_code == 200
    body = resp.json()
    assert body["coordinates"] == {"type": "Point", "coordinates": [-58.3816, -34.6037]}
    # La localidad se corta en el guión: sin devolver la consulta el pin no se explica.
    assert body["consulta"] == "Av. Corrientes 1000, CABA, Buenos Aires, AR"


def test_una_falla_del_geocoder_es_422_y_no_500(client, usuario_con, argentina, falso):
    falso(error=RoutingError("Sin coordenadas para Av. Inventada 1"))
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(GEOCODIFICAR, payload(), content_type="application/json")

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "business_rule"
    assert error["message"] == "Sin coordenadas para Av. Inventada 1"
    assert error["detail"]["motivo"] == "geocoder"


def test_sin_api_key_avisa_sin_nombrar_la_variable(client, usuario_con, argentina, settings):
    settings.ORS_API_KEY = ""
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(GEOCODIFICAR, payload(), content_type="application/json")

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["detail"]["motivo"] == "no_configurado"
    assert "ORS_API_KEY" not in error["message"]
    assert "mapa" in error["message"]


def test_un_pais_que_no_esta_en_la_tabla_es_422(client, usuario_con, argentina, falso):
    instancia = falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(GEOCODIFICAR, payload(pais_codigo="ZZ"), content_type="application/json")

    assert resp.status_code == 422
    assert resp.json()["error"]["detail"]["campo"] == "pais_codigo"
    assert instancia.consultas == []


def test_un_pais_que_el_geocoder_no_soporta_es_422(client, usuario_con, falso):
    Pais.objects.get_or_create(codigo="BR", defaults={"nombre": "Brasil"})
    # Sin falso instalado corre el adapter real, que rechaza el país antes de la red.
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(GEOCODIFICAR, payload(pais_codigo="BR"), content_type="application/json")

    assert resp.status_code == 422
    assert "no soportado" in resp.json()["error"]["message"]


def test_sin_ninguna_parte_de_la_direccion_no_se_consulta_al_geocoder(
    client, usuario_con, argentina, falso
):
    """Pelias con todo vacío devuelve el centroide del país, que se guardaría como válido."""
    instancia = falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    resp = client.post(
        GEOCODIFICAR,
        payload(calle="", localidad="   ", provincia=None),
        content_type="application/json",
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"
    assert instancia.consultas == []


def test_alcanza_con_el_permiso_de_crear(client, usuario_con, argentina, falso):
    falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_CREAR))

    assert client.post(GEOCODIFICAR, payload(), content_type="application/json").status_code == 200


def test_alcanza_con_el_permiso_de_editar(client, usuario_con, argentina, falso):
    """SessionAuth es OR: es la primera operación del repo que depende de eso."""
    falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_EDITAR))

    assert client.post(GEOCODIFICAR, payload(), content_type="application/json").status_code == 200


def test_solo_ver_no_alcanza(client, usuario_con, argentina, falso):
    falso(coordinate=BUENOS_AIRES)
    client.force_login(usuario_con(PermisoCodigo.UBICACIONES_VER))

    resp = client.post(GEOCODIFICAR, payload(), content_type="application/json")

    assert resp.status_code == 403
    assert resp.json()["error"]["detail"]["requiere"] == [
        "ubicaciones.crear",
        "ubicaciones.editar",
    ]


def test_sin_sesion_es_401(client, argentina):
    resp = client.post(GEOCODIFICAR, payload(), content_type="application/json")

    assert resp.status_code == 401
