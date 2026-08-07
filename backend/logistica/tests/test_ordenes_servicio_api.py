from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from catalog.enums import TipoCamion
from logistica.models import CostoOrdenServicio
from shared.permisos import PermisoCodigo
from tracking.services import RemitoService, TicketService
from transportista.enums import TipoOperacion, Via

pytestmark = pytest.mark.django_db

ORDENES = "/api/v1/ordenes-servicio/"
OPCIONES = "/api/v1/ordenes-servicio/opciones"


def detalle(orden_id: int) -> str:
    return f"/api/v1/ordenes-servicio/{orden_id}"


def costo(orden_id: int) -> str:
    return f"/api/v1/ordenes-servicio/{orden_id}/costo"


def orden_in(**extra) -> dict:
    payload = {
        "fecha_viaje": "2026-08-06T10:00:00-03:00",
        "tipo_operacion": TipoOperacion.CARGA.value,
        "tipo_camion": TipoCamion.SEMI.value,
        "via": Via.TERRESTRE.value,
        "hombreador": False,
        "facturable": True,
    }
    payload.update(extra)
    return payload


@pytest.fixture
def usuario_con(crear_usuario, crear_rol, asignar_rol):
    def _crear(*codigos: PermisoCodigo):
        user = crear_usuario()
        asignar_rol(user, crear_rol("rol", *codigos))
        return user

    return _crear


@pytest.fixture
def crear_costo():
    def _crear(orden, total: str = "185000.00") -> CostoOrdenServicio:
        return CostoOrdenServicio.objects.create(
            orden_servicio=orden,
            precio_flete=Decimal(total),
            dias=3,
            precio_dia=None,
            tipo_operacion=orden.tipo_operacion,
            hombreador=orden.hombreador,
            cantidad_destinos=1,
            fecha_viaje=orden.fecha_viaje,
        )

    return _crear


@pytest.fixture
def crear_ticket():
    def _crear(orden, numero: str, egreso: datetime | None = None):
        # La planta del ticket es el origen de la OS, que la fixture crea como PLANTA.
        return TicketService.create_ticket(
            planta=orden.origen,
            numero=numero,
            orden_servicio=orden,
            fecha_ingreso=orden.fecha_viaje or datetime(2026, 8, 6, 13, 0, tzinfo=UTC),
            fecha_egreso=egreso,
        )

    return _crear


@pytest.fixture
def crear_remito(crear_ubicacion):
    contador = iter(range(500, 600))

    def _crear(orden, numero: str, destinos: list | None = None):
        return RemitoService.create_remito(
            numero=numero,
            fecha=None,
            orden_servicio=orden,
            destinos=destinos or [crear_ubicacion(f"CL{next(contador)}")],
        )

    return _crear


def test_opciones_devuelve_los_tres_enums_completos(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(OPCIONES)

    assert resp.status_code == 200
    body = resp.json()
    assert [o["value"] for o in body["tipos_operacion"]] == [t.value for t in TipoOperacion]
    assert [o["value"] for o in body["tipos_camion"]] == [t.value for t in TipoCamion]
    assert [o["value"] for o in body["vias"]] == [v.value for v in Via]
    assert body["tipos_camion"][0]["label"] == "Chasis"


def test_lista_desnormaliza_origen_y_transportista(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(ORDENES)

    assert resp.status_code == 200
    fila = resp.json()[0]
    assert fila["id"] == orden.id
    assert fila["origen_codigo"] == "PL01"
    assert fila["origen_nombre"] == "Planta"
    assert fila["transportista_razon_social"] == "Fletes SA"
    assert fila["costo"] is None


def test_lista_filtra_por_facturable(client, usuario_con, crear_orden):
    facturable = crear_orden(facturable=True)
    crear_orden(facturable=False)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(ORDENES, {"facturable": "true"})

    assert resp.status_code == 200
    assert [o["id"] for o in resp.json()] == [facturable.id]


def test_lista_filtra_por_con_costo(client, usuario_con, crear_orden, crear_costo):
    con_costo = crear_orden()
    sin_costo = crear_orden()
    crear_costo(con_costo)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert [o["id"] for o in client.get(ORDENES, {"con_costo": "true"}).json()] == [con_costo.id]
    assert [o["id"] for o in client.get(ORDENES, {"con_costo": "false"}).json()] == [sin_costo.id]


def test_un_costo_dado_de_baja_no_cuenta_como_con_costo(
    client, usuario_con, crear_orden, crear_costo
):
    orden = crear_orden()
    crear_costo(orden).delete()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert [o["id"] for o in client.get(ORDENES, {"con_costo": "false"}).json()] == [orden.id]
    assert client.get(detalle(orden.id)).json()["costo"] is None


def test_detalle_trae_el_costo_vigente(client, usuario_con, crear_orden, crear_costo):
    orden = crear_orden()
    crear_costo(orden, total="185000.00")
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(detalle(orden.id))

    assert resp.status_code == 200
    # Decimal viaja como string.
    assert resp.json()["costo"]["total"] == "185000.00"


def test_detalle_de_una_orden_inexistente_da_not_found(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(detalle(9999))

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_put_persiste_los_seis_campos(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_EDITAR))

    resp = client.put(
        detalle(orden.id),
        orden_in(
            tipo_operacion=TipoOperacion.CAMARA.value,
            tipo_camion=TipoCamion.BALANCIN.value,
            via=Via.MARITIMA.value,
            hombreador=True,
            facturable=False,
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    orden.refresh_from_db()
    assert orden.tipo_operacion == TipoOperacion.CAMARA.value
    assert orden.tipo_camion == TipoCamion.BALANCIN.value
    assert orden.via == Via.MARITIMA.value
    assert orden.hombreador is True
    assert orden.facturable is False
    assert orden.fecha_viaje.isoformat() == "2026-08-06T13:00:00+00:00"


def test_put_acepta_limpiar_fecha_viaje_y_tipo_camion(client, usuario_con, crear_orden):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_EDITAR))

    resp = client.put(
        detalle(orden.id),
        orden_in(fecha_viaje=None, tipo_camion=None),
        content_type="application/json",
    )

    assert resp.status_code == 200
    orden.refresh_from_db()
    assert orden.fecha_viaje is None
    assert orden.tipo_camion is None


def test_put_con_fecha_naive_da_payload_invalid(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_EDITAR))

    resp = client.put(
        detalle(orden.id),
        orden_in(fecha_viaje="2026-08-06T10:00:00"),
        content_type="application/json",
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_put_con_tipo_camion_invalido_da_payload_invalid(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_EDITAR))

    resp = client.put(
        detalle(orden.id), orden_in(tipo_camion="camioneta"), content_type="application/json"
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_ver_no_alcanza_para_editar(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.put(detalle(orden.id), orden_in(), content_type="application/json")

    # 403 y no 401: el usuario está logueado, la SPA no lo tiene que desloguear.
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
    assert resp.json()["error"]["detail"]["requiere"] == ["ordenes_servicio.editar"]


def test_sin_sesion_da_unauthorized(client, crear_orden):
    crear_orden()

    resp = client.get(ORDENES)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_busca_por_un_pedazo_del_numero_de_ticket(
    client, usuario_con, crear_orden, crear_ticket
):
    con_ticket = crear_orden()
    crear_ticket(con_ticket, "TCK-0012345-A")
    crear_ticket(crear_orden(), "TCK-0099999-A")
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(ORDENES, {"numero": "12345"})

    assert resp.status_code == 200
    assert [o["id"] for o in resp.json()] == [con_ticket.id]


def test_busca_por_numero_de_remito_en_la_misma_caja(
    client, usuario_con, crear_orden, crear_remito
):
    con_remito = crear_orden()
    crear_remito(con_remito, "0001-00000012")
    crear_remito(crear_orden(), "0001-00099999")
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(ORDENES, {"numero": "00000012"})

    assert resp.status_code == 200
    assert [o["id"] for o in resp.json()] == [con_remito.id]


def test_una_os_con_dos_coincidencias_aparece_una_sola_vez(
    client, usuario_con, crear_orden, crear_ticket, crear_remito
):
    # Sin distinct() los joins multivaluados devuelven la misma OS repetida.
    orden = crear_orden()
    crear_ticket(orden, "TCK-0012345-A")
    crear_ticket(orden, "TCK-0012345-B")
    crear_remito(orden, "0001-00012345")
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(ORDENES, {"numero": "12345"})

    assert [o["id"] for o in resp.json()] == [orden.id]


def test_un_ticket_dado_de_baja_no_hace_matchear_su_os(
    client, usuario_con, crear_orden, crear_ticket
):
    orden = crear_orden()
    crear_ticket(orden, "TCK-0012345-A").delete()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert client.get(ORDENES, {"numero": "12345"}).json() == []
    assert client.get(detalle(orden.id)).json()["tickets"] == []


def test_el_rango_de_fechas_se_resuelve_en_hora_argentina(
    client, usuario_con, crear_orden
):
    # 02:00Z del 6 son las 23:00 del 5 en Buenos Aires.
    orden = crear_orden(fecha_viaje=datetime(2026, 8, 6, 2, 0, tzinfo=UTC))
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    en_el_cinco = client.get(ORDENES, {"fecha_viaje_hasta": "2026-08-05"}).json()
    en_el_seis = client.get(ORDENES, {"fecha_viaje_desde": "2026-08-06"}).json()

    assert orden.id in [o["id"] for o in en_el_cinco]
    assert orden.id not in [o["id"] for o in en_el_seis]


def test_hasta_incluye_el_dia_entero(client, usuario_con, crear_orden):
    # 23:00 del 6 en Buenos Aires es 02:00Z del 7.
    orden = crear_orden(fecha_viaje=datetime(2026, 8, 7, 2, 0, tzinfo=UTC))
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.get(
        ORDENES, {"fecha_viaje_desde": "2026-08-06", "fecha_viaje_hasta": "2026-08-06"}
    )

    assert [o["id"] for o in resp.json()] == [orden.id]


def test_una_os_sin_fecha_viaje_no_entra_en_ningun_rango(
    client, usuario_con, crear_orden
):
    sin_fecha = crear_orden(fecha_viaje=None)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert sin_fecha.id in [o["id"] for o in client.get(ORDENES).json()]
    resp = client.get(ORDENES, {"fecha_viaje_desde": "2020-01-01"})
    assert sin_fecha.id not in [o["id"] for o in resp.json()]


def test_incluir_sin_fecha_las_trae_junto_con_el_rango(client, usuario_con, crear_orden):
    en_rango = crear_orden(fecha_viaje=datetime(2026, 8, 6, 13, 0, tzinfo=UTC))
    sin_fecha = crear_orden(fecha_viaje=None)
    crear_orden(fecha_viaje=datetime(2020, 1, 1, 13, 0, tzinfo=UTC))
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    rango = {"fecha_viaje_desde": "2026-08-06", "fecha_viaje_hasta": "2026-08-06"}
    resp = client.get(ORDENES, rango | {"incluir_sin_fecha": "true"})

    assert sorted(o["id"] for o in resp.json()) == sorted([en_rango.id, sin_fecha.id])


def test_incluir_sin_fecha_sin_rango_no_cambia_nada(client, usuario_con, crear_orden):
    crear_orden()
    crear_orden(fecha_viaje=None)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    sin_flag = client.get(ORDENES).json()
    con_flag = client.get(ORDENES, {"incluir_sin_fecha": "true"}).json()

    assert [o["id"] for o in sin_flag] == [o["id"] for o in con_flag]


def test_la_lista_trae_los_tickets_pero_no_los_remitos(
    client, usuario_con, crear_orden, crear_ticket, crear_remito
):
    orden = crear_orden()
    crear_ticket(orden, "TCK-0012345-A")
    crear_remito(orden, "0001-00000012")
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    fila = next(o for o in client.get(ORDENES).json() if o["id"] == orden.id)

    assert [t["numero"] for t in fila["tickets"]] == ["TCK-0012345-A"]
    assert "remitos" not in fila


def test_el_detalle_trae_tickets_remitos_y_destinos(
    client, usuario_con, crear_orden, crear_ticket, crear_remito, crear_ubicacion
):
    orden = crear_orden()
    crear_ticket(orden, "TCK-0012345-A", egreso=datetime(2026, 8, 7, 13, 0, tzinfo=UTC))
    crear_remito(orden, "0001-00000012", [crear_ubicacion("CL700"), crear_ubicacion("CL701")])
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    body = client.get(detalle(orden.id)).json()

    ticket = body["tickets"][0]
    assert ticket["numero"] == "TCK-0012345-A"
    assert ticket["planta_codigo"] == "PL01"
    assert ticket["fecha_egreso"] is not None

    remito = body["remitos"][0]
    assert remito["numero"] == "0001-00000012"
    assert [d["codigo"] for d in remito["destinos"]] == ["CL700", "CL701"]
    assert remito["destinos"][0]["pais"] is not None


def test_un_destino_dado_de_baja_no_viaja_en_el_detalle(
    client, usuario_con, crear_orden, crear_remito, crear_ubicacion
):
    orden = crear_orden()
    remito = crear_remito(orden, "0001-00000012", [crear_ubicacion("CL700")])
    remito.destinos.first().delete()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    body = client.get(detalle(orden.id)).json()

    assert body["remitos"][0]["destinos"] == []


def test_la_estadia_de_un_ticket_que_entra_y_sale_el_mismo_dia_es_cero(
    client, usuario_con, crear_orden, crear_ticket
):
    orden = crear_orden()
    ticket = crear_ticket(orden, "TCK-1", egreso=datetime(2026, 8, 6, 20, 0, tzinfo=UTC))
    ticket.fecha_ingreso = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
    ticket.save(update_fields=["fecha_ingreso", "updated_at"])
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert client.get(detalle(orden.id)).json()["tickets"][0]["dias_estadia"] == 0


def test_la_estadia_cuenta_por_dia_argentino_no_por_horas(
    client, usuario_con, crear_orden, crear_ticket
):
    # 23:00 del 6 y 01:00 del 7 en Buenos Aires: dos horas, pero cambió el día -> 1.
    orden = crear_orden()
    ticket = crear_ticket(orden, "TCK-1", egreso=datetime(2026, 8, 7, 4, 0, tzinfo=UTC))
    ticket.fecha_ingreso = datetime(2026, 8, 7, 2, 0, tzinfo=UTC)
    ticket.save(update_fields=["fecha_ingreso", "updated_at"])
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert client.get(detalle(orden.id)).json()["tickets"][0]["dias_estadia"] == 1


def test_la_suma_de_estadias_es_la_permanencia_que_se_cobra(crear_orden, crear_ticket):
    orden = crear_orden()
    crear_ticket(orden, "TCK-1", egreso=datetime(2026, 8, 8, 13, 0, tzinfo=UTC))
    crear_ticket(orden, "TCK-2", egreso=datetime(2026, 8, 9, 13, 0, tzinfo=UTC))

    tickets = TicketService.list_by_ordenes_servicio([orden.id])[orden.id]
    assert sum(TicketService.dias_estadia(t) or 0 for t in tickets) == (
        TicketService.get_dias_permanencia(orden.id)
    )


def test_un_ticket_sin_egreso_no_rompe_la_lista(client, usuario_con, crear_orden, crear_ticket):
    # get_dias_permanencia levanta acá, pero ver la OS tiene que funcionar igual:
    # que no se pueda costear no puede impedir mostrarla.
    orden = crear_orden()
    crear_ticket(orden, "TCK-1", egreso=None)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    fila = next(o for o in client.get(ORDENES).json() if o["id"] == orden.id)

    assert fila["tickets"][0]["dias_estadia"] is None


def test_un_ticket_sin_egreso_viaja_como_null(client, usuario_con, crear_orden, crear_ticket):
    # Es lo que la pantalla marca: sin egreso, el costeo falla con TicketSinEgresoError.
    orden = crear_orden()
    crear_ticket(orden, "TCK-0012345-A", egreso=None)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    assert client.get(detalle(orden.id)).json()["tickets"][0]["fecha_egreso"] is None


def test_costo_ya_no_acepta_api_key(client, usuario_con, crear_orden, settings):
    orden = crear_orden()
    settings.INGEST_API_KEY = "una-key"

    resp = client.post(costo(orden.id), HTTP_X_API_KEY="una-key")

    assert resp.status_code == 401


def test_costo_por_sesion_sin_el_permiso_da_forbidden(client, usuario_con, crear_orden):
    orden = crear_orden()
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER))

    resp = client.post(costo(orden.id))

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_costo_por_sesion_llega_al_use_case(client, usuario_con, crear_orden):
    orden = crear_orden(facturable=False)
    client.force_login(usuario_con(PermisoCodigo.ORDENES_SERVICIO_CALCULAR_COSTO))

    resp = client.post(costo(orden.id))

    # Pasó la auth y murió en la regla de negocio, que es lo que se quiere verificar.
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "business_rule"
