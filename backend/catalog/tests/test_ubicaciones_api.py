from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point

from catalog.enums import SRID_WGS84, TipoUbicacion
from catalog.models import Pais, Ubicacion
from catalog.services import UbicacionService
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


# --- Alta ---------------------------------------------------------------------------------


@pytest.fixture
def argentina(db):
    return Pais.objects.get_or_create(codigo="AR", defaults={"nombre": "Argentina"})[0]


@pytest.fixture
def creador(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario(email="creador@tms.test")
    asignar_rol(
        user,
        crear_rol("alta", PermisoCodigo.UBICACIONES_VER, PermisoCodigo.UBICACIONES_CREAR),
    )
    return user


def ubicacion_crear_in(**extra) -> dict:
    cuerpo = {
        "nombre": "Expreso del Litoral",
        "tipo": "expreso",
        "calle": "Av. Pellegrini 1500",
        "localidad": "Rosario",
        "provincia": "Santa Fe",
        "pais_codigo": "AR",
        "coordinates": {"type": "Point", "coordinates": [-60.6393, -32.9442]},
    }
    cuerpo.update(extra)
    return cuerpo


def test_el_alta_crea_una_ubicacion_validada(client, creador, argentina):
    client.force_login(creador)

    resp = client.post(UBICACIONES, ubicacion_crear_in(), content_type="application/json")

    assert resp.status_code == 201
    body = resp.json()
    assert body["validada"] is True
    assert body["codigo"] is None
    assert body["tipo"] == "expreso"
    assert body["localidad"] == "Rosario"
    assert body["pais"] == "Argentina"
    assert body["coordinates"] == {"type": "Point", "coordinates": [-60.6393, -32.9442]}


def test_un_codigo_en_blanco_queda_nulo(client, creador, argentina):
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(codigo="   "), content_type="application/json"
    )

    assert resp.status_code == 201
    assert resp.json()["codigo"] is None


def test_un_codigo_repetido_es_409(client, creador, argentina, crear_ubicacion):
    crear_ubicacion("Ya existe", "EXP01")
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(codigo="EXP01"), content_type="application/json"
    )

    assert resp.status_code == 409
    error = resp.json()["error"]
    assert error["code"] == "conflict"
    assert error["detail"]["codigo"] == "EXP01"


def test_se_puede_reusar_el_codigo_de_una_dada_de_baja(client, creador, argentina, crear_ubicacion):
    """La unique es parcial sobre active=True: la fila muerta no bloquea ni resucita."""
    vieja = crear_ubicacion("Dada de baja", "EXP02")
    vieja.delete()
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(codigo="EXP02"), content_type="application/json"
    )

    assert resp.status_code == 201
    assert Ubicacion.all_objects.get(pk=vieja.pk).active is False
    viva = UbicacionService.get_ubicacion_by_codigo("EXP02")
    assert viva is not None
    assert viva.id == resp.json()["id"]


@pytest.mark.parametrize("calle", ["", "   "])
def test_una_calle_en_blanco_es_422_de_payload(client, creador, argentina, calle):
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(calle=calle), content_type="application/json"
    )

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "payload_invalid"
    assert any(e["loc"][-1] == "calle" for e in error["detail"]["errors"])


def test_una_calle_larguisima_es_422_y_no_500(client, creador, argentina):
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(calle="x" * 300), content_type="application/json"
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_el_alta_sin_coordenada_es_422(client, creador, argentina):
    cuerpo = ubicacion_crear_in()
    del cuerpo["coordinates"]
    client.force_login(creador)

    resp = client.post(UBICACIONES, cuerpo, content_type="application/json")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_una_coordenada_fuera_de_rango_es_business_rule(client, creador, argentina):
    client.force_login(creador)

    resp = client.post(
        UBICACIONES,
        ubicacion_crear_in(coordinates={"type": "Point", "coordinates": [-60.0, 999.0]}),
        content_type="application/json",
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "business_rule"


def test_una_planta_sin_codigo_es_422(client, creador, argentina):
    """La ingesta busca la planta por código: sin código no puede ser origen de nada."""
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(tipo="planta"), content_type="application/json"
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_un_pais_inexistente_es_422_y_no_404(client, creador, argentina):
    client.force_login(creador)

    resp = client.post(
        UBICACIONES, ubicacion_crear_in(pais_codigo="ZZ"), content_type="application/json"
    )

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "business_rule"
    assert error["detail"]["campo"] == "pais_codigo"


def test_el_alta_con_solo_editar_da_403(client, editor, argentina):
    client.force_login(editor)

    resp = client.post(UBICACIONES, ubicacion_crear_in(), content_type="application/json")

    assert resp.status_code == 403
    assert resp.json()["error"]["detail"]["requiere"] == [PermisoCodigo.UBICACIONES_CREAR.value]


def test_el_put_ignora_la_calle_y_el_codigo_que_le_manden(client, editor, crear_ubicacion):
    """Hoy sólo lo sostiene el extra="ignore" de pydantic; este test lo fija."""
    ubicacion = crear_ubicacion("Original", "CL100", validada=False)
    client.force_login(editor)

    resp = client.put(
        f"{UBICACIONES}{ubicacion.id}",
        ubicacion_in() | {"calle": "Pisada 1", "codigo": "PISADO"},
        content_type="application/json",
    )

    assert resp.status_code == 200
    ubicacion.refresh_from_db()
    assert ubicacion.calle == "Av. Siempre Viva 742"
    assert ubicacion.codigo == "CL100"


# --- Opciones -----------------------------------------------------------------------------


def test_las_opciones_traen_los_tipos_del_enum_y_los_paises(client, lector, argentina):
    client.force_login(lector)

    resp = client.get(f"{UBICACIONES}opciones")

    assert resp.status_code == 200
    body = resp.json()
    assert [o["value"] for o in body["tipos_ubicacion"]] == [t.value for t in TipoUbicacion]
    assert {"codigo": "AR", "nombre": "Argentina"} in body["paises"]


def test_las_opciones_sin_permiso_dan_403(client, crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario(email="pelado@tms.test")
    asignar_rol(user, crear_rol("nada"))
    client.force_login(user)

    assert client.get(f"{UBICACIONES}opciones").status_code == 403
