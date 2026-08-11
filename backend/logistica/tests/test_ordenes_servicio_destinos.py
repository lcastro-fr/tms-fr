from __future__ import annotations

from decimal import Decimal

import pytest

from catalog.enums import TipoCamion, TipoUbicacion
from logistica.enums import OrigenDestinos
from logistica.models import CostoOrdenServicio, OrdenServicioDestino
from shared.permisos import PermisoCodigo
from tracking.services import RemitoService, TicketService
from transportista.enums import TipoOperacion, Via

pytestmark = pytest.mark.django_db

ORDENES = "/api/v1/ordenes-servicio/"
OPCIONES = "/api/v1/ordenes-servicio/opciones"


def detalle(orden_id: int) -> str:
    return f"/api/v1/ordenes-servicio/{orden_id}"


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
def editor(client, usuario_con):
    client.force_login(
        usuario_con(PermisoCodigo.ORDENES_SERVICIO_VER, PermisoCodigo.ORDENES_SERVICIO_EDITAR)
    )
    return client


@pytest.fixture
def expreso(crear_ubicacion):
    return crear_ubicacion("EXP01", tipo=TipoUbicacion.EXPRESO.value, nombre="Expreso del Litoral")


def ids_activos(orden) -> list[int]:
    return list(
        OrdenServicioDestino.objects.filter(orden_servicio=orden)
        .order_by("secuencia")
        .values_list("ubicacion_id", flat=True)
    )


def test_el_put_persiste_los_destinos_en_el_orden_del_payload(
    editor, crear_orden, crear_ubicacion, expreso
):
    orden = crear_orden()
    otro = crear_ubicacion("CL001")

    resp = editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": expreso.id}, {"ubicacion_id": otro.id}]),
        content_type="application/json",
    )

    assert resp.status_code == 200
    filas = OrdenServicioDestino.objects.filter(orden_servicio=orden).order_by("secuencia")
    assert [(f.ubicacion_id, f.secuencia) for f in filas] == [(expreso.id, 0), (otro.id, 1)]


def test_omitir_destinos_no_toca_los_existentes(editor, crear_orden, expreso):
    orden = crear_orden()
    editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": expreso.id}]),
        content_type="application/json",
    )

    resp = editor.put(detalle(orden.id), orden_in(hombreador=True), content_type="application/json")

    assert resp.status_code == 200
    assert ids_activos(orden) == [expreso.id]


def test_una_lista_vacia_borra_los_destinos_y_vuelven_a_decidir_los_remitos(
    editor, crear_orden, crear_ubicacion, expreso
):
    orden = crear_orden()
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL002")],
    )
    editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": expreso.id}]),
        content_type="application/json",
    )

    resp = editor.put(detalle(orden.id), orden_in(destinos=[]), content_type="application/json")

    assert resp.status_code == 200
    assert ids_activos(orden) == []
    assert editor.get(detalle(orden.id)).json()["origen_destinos"] == OrigenDestinos.REMITOS.value


def test_un_destino_repetido_es_422_y_no_un_500(editor, crear_orden, expreso):
    orden = crear_orden()

    resp = editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": expreso.id}, {"ubicacion_id": expreso.id}]),
        content_type="application/json",
    )

    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "business_rule"
    assert body["detail"]["indice"] == 1


def test_una_ubicacion_inexistente_es_422_y_no_un_500(editor, crear_orden):
    orden = crear_orden()

    resp = editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": 999_999}]),
        content_type="application/json",
    )

    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "business_rule"
    assert body["detail"]["ids"] == [999_999]


def test_reguardar_los_mismos_destinos_no_crea_una_generacion_nueva(editor, crear_orden, expreso):
    orden = crear_orden()
    payload = orden_in(destinos=[{"ubicacion_id": expreso.id}])
    editor.put(detalle(orden.id), payload, content_type="application/json")
    fila = OrdenServicioDestino.all_objects.get(orden_servicio=orden)

    editor.put(detalle(orden.id), payload, content_type="application/json")

    assert OrdenServicioDestino.all_objects.filter(orden_servicio=orden).count() == 1
    assert OrdenServicioDestino.all_objects.get(orden_servicio=orden).id == fila.id


def test_el_detalle_abre_aunque_los_remitos_no_se_puedan_resolver(
    editor, crear_orden, crear_ubicacion
):
    """Si el detalle resolviera los destinos, esta OS sería imposible de abrir y de arreglar."""
    orden = crear_orden(via=Via.TERRESTRE.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL999", pais="UY")],
    )

    resp = editor.get(detalle(orden.id))

    assert resp.status_code == 200
    body = resp.json()
    assert [d["codigo"] for d in body["destinos_sugeridos"]] == ["CL999"]
    assert body["origen_destinos"] == OrigenDestinos.REMITOS.value


def test_el_detalle_deduplica_los_sugeridos_entre_remitos(editor, crear_orden, crear_ubicacion):
    orden = crear_orden()
    compartido = crear_ubicacion("CL003")
    RemitoService.create_remito(
        numero="0001-00000001", fecha=None, orden_servicio=orden, destinos=[compartido]
    )
    RemitoService.create_remito(
        numero="0001-00000002", fecha=None, orden_servicio=orden, destinos=[compartido]
    )

    body = editor.get(detalle(orden.id)).json()

    assert [d["codigo"] for d in body["destinos_sugeridos"]] == ["CL003"]


def test_el_detalle_marca_los_destinos_sin_coordenadas(editor, crear_orden, crear_ubicacion):
    orden = crear_orden()
    sin_punto = crear_ubicacion("CL004")
    sin_punto.coordinates = None
    sin_punto.save(update_fields=["coordinates"])
    editor.put(
        detalle(orden.id),
        orden_in(destinos=[{"ubicacion_id": sin_punto.id}]),
        content_type="application/json",
    )

    body = editor.get(detalle(orden.id)).json()

    assert body["destinos"][0]["tiene_coordenadas"] is False
    assert body["origen_destinos"] == OrigenDestinos.EXPLICITOS.value


def test_el_detalle_de_una_camara_dice_que_los_destinos_no_aplican(editor, crear_orden, expreso):
    orden = crear_orden(tipo_operacion=TipoOperacion.CAMARA.value)
    editor.put(
        detalle(orden.id),
        orden_in(
            tipo_operacion=TipoOperacion.CAMARA.value, destinos=[{"ubicacion_id": expreso.id}]
        ),
        content_type="application/json",
    )

    body = editor.get(detalle(orden.id)).json()

    assert body["origen_destinos"] == OrigenDestinos.NO_APLICA.value
    assert [d["ubicacion_id"] for d in body["destinos"]] == [expreso.id]


def test_las_opciones_no_se_caen_con_una_ubicacion_sin_pais(editor, crear_ubicacion):
    """La ingesta crea ubicaciones sin país; una sola alcanzaba para 500 este endpoint."""
    sin_pais = crear_ubicacion("CL900", pais=None)

    resp = editor.get(OPCIONES)

    assert resp.status_code == 200
    opcion = next(u for u in resp.json()["ubicaciones"] if u["id"] == sin_pais.id)
    assert opcion["pais"] is None


def test_las_opciones_traen_las_ubicaciones_con_tipo_y_coordenadas(editor, expreso):
    body = editor.get(OPCIONES).json()

    opcion = next(u for u in body["ubicaciones"] if u["id"] == expreso.id)
    assert opcion["tipo"] == TipoUbicacion.EXPRESO.value
    assert opcion["tiene_coordenadas"] is True
    assert opcion["codigo"] == "EXP01"


def test_editar_los_destinos_desactualiza_el_costo_guardado(editor, crear_orden, expreso):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    CostoOrdenServicio.objects.create(
        orden_servicio=orden,
        precio_flete=Decimal("185000.00"),
        dias=0,
        tipo_operacion=orden.tipo_operacion,
        modalidad="directo",
        tipo_camion=TipoCamion.SEMI.value,
        hombreador=orden.hombreador,
        cantidad_destinos=1,
        fecha_viaje=orden.fecha_viaje,
    )
    assert editor.get(detalle(orden.id)).json()["costo_desactualizado"] is False

    editor.put(
        detalle(orden.id),
        orden_in(
            destinos=[
                {"ubicacion_id": expreso.id},
                {"ubicacion_id": orden.origen_id},
            ]
        ),
        content_type="application/json",
    )

    assert editor.get(detalle(orden.id)).json()["costo_desactualizado"] is True


def test_un_ticket_sin_egreso_no_impide_ver_el_costo_desactualizado(
    editor, crear_orden, crear_ubicacion
):
    """`dias` queda afuera de la comparación justamente para que esto no levante."""
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    TicketService.create_ticket(
        planta=orden.origen,
        numero="T-1",
        orden_servicio=orden,
        fecha_ingreso=orden.fecha_viaje,
        fecha_egreso=None,
    )
    CostoOrdenServicio.objects.create(
        orden_servicio=orden,
        precio_flete=Decimal("100.00"),
        dias=1,
        tipo_operacion=orden.tipo_operacion,
        modalidad="directo",
        tipo_camion=TipoCamion.SEMI.value,
        hombreador=orden.hombreador,
        cantidad_destinos=1,
        fecha_viaje=orden.fecha_viaje,
    )

    resp = editor.get(detalle(orden.id))

    assert resp.status_code == 200
    assert resp.json()["costo_desactualizado"] is False
