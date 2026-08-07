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
    def _crear(
        nombre: str,
        codigo: str,
        coordinates: Point | None = None,
        validada: bool = True,
    ) -> Ubicacion:
        return Ubicacion.objects.create(
            nombre=nombre,
            codigo=codigo,
            calle="Av. Siempre Viva 742",
            localidad="Rosario",
            provincia="Santa Fe",
            coordinates=coordinates,
            validada=validada,
        )

    return _crear


@pytest.fixture
def editor(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(
        user,
        crear_rol("edicion", PermisoCodigo.UBICACIONES_VER, PermisoCodigo.UBICACIONES_EDITAR),
    )
    return user


def ubicacion_in(nombre: str = "Corregida", tipo: str = "planta") -> dict:
    return {
        "nombre": nombre,
        "tipo": tipo,
        "coordinates": {"type": "Point", "coordinates": [-58.3816, -34.6037]},
    }


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


def test_filtra_por_validada(client, lector, crear_ubicacion):
    crear_ubicacion("Revisada", "CL100", validada=True)
    crear_ubicacion("Pendiente", "CL200", validada=False)
    client.force_login(lector)

    def nombres(query: str) -> list[str]:
        return [u["nombre"] for u in client.get(f"{UBICACIONES}{query}").json()]

    assert nombres("?validada=false") == ["Pendiente"]
    assert nombres("?validada=true") == ["Revisada"]
    assert sorted(nombres("")) == ["Pendiente", "Revisada"]


def test_filtra_por_con_coordenadas(client, lector, crear_ubicacion):
    crear_ubicacion("Con punto", "CL100", Point(-58.4, -34.6, srid=SRID_WGS84), validada=True)
    crear_ubicacion("Sin punto", "CL200", None, validada=True)
    client.force_login(lector)

    def nombres(query: str) -> list[str]:
        return [u["nombre"] for u in client.get(f"{UBICACIONES}{query}").json()]

    assert nombres("?con_coordenadas=false") == ["Sin punto"]
    assert nombres("?con_coordenadas=true") == ["Con punto"]
    assert nombres("?validada=false") == []
    assert nombres("?validada=true&con_coordenadas=false") == ["Sin punto"]


def test_actualizar_corrige_la_coordenada_y_valida(client, editor, crear_ubicacion):
    ubicacion = crear_ubicacion("Sin geo", "CL100", validada=False)
    client.force_login(editor)

    resp = client.put(
        f"{UBICACIONES}{ubicacion.id}",
        ubicacion_in(),
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["nombre"] == "Corregida"
    assert body["tipo"] == "planta"
    assert body["coordinates"]["coordinates"] == pytest.approx([-58.3816, -34.6037])
    assert body["validada"] is True
    assert client.get(f"{UBICACIONES}?validada=false").json() == []


def test_actualizar_no_toca_el_codigo(client, editor, crear_ubicacion):
    ubicacion = crear_ubicacion("Sin geo", "CL100", validada=False)
    client.force_login(editor)

    client.put(f"{UBICACIONES}{ubicacion.id}", ubicacion_in(), content_type="application/json")

    ubicacion.refresh_from_db()
    assert ubicacion.codigo == "CL100"


def test_una_latitud_fuera_de_rango_da_business_rule(client, editor, crear_ubicacion):
    ubicacion = crear_ubicacion("Sin geo", "CL100", validada=False)
    client.force_login(editor)

    payload = ubicacion_in()
    payload["coordinates"]["coordinates"] = [-58.3816, 999.0]

    resp = client.put(f"{UBICACIONES}{ubicacion.id}", payload, content_type="application/json")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "business_rule"


def test_un_tipo_invalido_lo_ataja_pydantic(client, editor, crear_ubicacion):
    ubicacion = crear_ubicacion("Sin geo", "CL100", validada=False)
    client.force_login(editor)

    resp = client.put(
        f"{UBICACIONES}{ubicacion.id}",
        ubicacion_in(tipo="galpon"),
        content_type="application/json",
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_actualizar_sin_permiso_da_403_y_no_401(client, lector, crear_ubicacion):
    ubicacion = crear_ubicacion("Sin geo", "CL100", validada=False)
    client.force_login(lector)

    resp = client.put(
        f"{UBICACIONES}{ubicacion.id}", ubicacion_in(), content_type="application/json"
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["detail"]["requiere"] == [PermisoCodigo.UBICACIONES_EDITAR.value]


def test_actualizar_una_inexistente_da_404(client, editor):
    client.force_login(editor)

    resp = client.put(f"{UBICACIONES}9999", ubicacion_in(), content_type="application/json")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
