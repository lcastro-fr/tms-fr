from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from catalog.enums import TipoCamion
from logistica.services import OrdenServicioService
from tracking.services import RemitoService
from tracking.use_cases import CalcularCostoOrdenServicioUseCase
from transportista.enums import ModalidadFlete, Via
from transportista.models import TarifaFlete
from transportista.services import TarifarioService

pytestmark = pytest.mark.django_db

VIGENTE_DESDE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def tarifario(transportista):
    return TarifarioService.create_tarifario(
        transportista_id=transportista.id, vigente_desde=VIGENTE_DESDE
    )


def tarifa_por_ubicacion(tarifario, ubicacion, precio: str, modalidad: ModalidadFlete):
    return TarifaFlete.objects.create(
        tarifario=tarifario,
        ubicacion=ubicacion,
        modalidad=modalidad.value,
        tipo_camion=TipoCamion.SEMI.value,
        hombreador=False,
        precio=Decimal(precio),
    )


def test_una_os_maritima_a_destino_extranjero_se_costea_contra_el_puerto(
    crear_orden, crear_ubicacion, puerto, tarifario
):
    orden = crear_orden(via=Via.MARITIMA.value, tipo_camion=TipoCamion.SEMI.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL999", pais="UY")],
    )
    tarifa_por_ubicacion(tarifario, puerto, "185000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("185000.00")
    assert costo.cantidad_destinos == 1
    assert costo.modalidad == ModalidadFlete.DIRECTO.value


def test_los_destinos_del_costo_son_los_resueltos_no_los_crudos(
    crear_orden, crear_ubicacion, puerto, tarifario
):
    orden = crear_orden(via=Via.MARITIMA.value, tipo_camion=TipoCamion.SEMI.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[
            crear_ubicacion("CL997", pais="UY"),
            crear_ubicacion("CL998", pais="BR"),
            crear_ubicacion("CL999", pais="CL"),
        ],
    )
    tarifa_por_ubicacion(tarifario, puerto, "185000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.cantidad_destinos == 1


def test_una_os_no_facturable_no_se_costea(crear_orden, tarifario):
    orden = crear_orden(facturable=False, tipo_camion=TipoCamion.SEMI.value)

    with pytest.raises(CalcularCostoOrdenServicioUseCase.OrdenServicioNoFacturable):
        CalcularCostoOrdenServicioUseCase.execute(orden.id)


def test_una_os_terrestre_con_destino_extranjero_no_se_costea(
    crear_orden, crear_ubicacion, tarifario
):
    orden = crear_orden(via=Via.TERRESTRE.value, tipo_camion=TipoCamion.SEMI.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL999", pais="UY")],
    )

    with pytest.raises(OrdenServicioService.ViaSinDestinoDefaultError):
        CalcularCostoOrdenServicioUseCase.execute(orden.id)
