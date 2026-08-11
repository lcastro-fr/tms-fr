from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from catalog.enums import TipoCamion, TipoUbicacion
from logistica.services import OrdenServicioService
from tracking.services import RemitoService
from tracking.use_cases import CalcularCostoOrdenServicioUseCase
from transportista.enums import ConceptoUnidadMedida, ModalidadFlete, TipoOperacion, Via
from transportista.models import ConceptoAdicional, TarifaConceptoAdicional, TarifaFlete
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


def test_una_os_terrestre_por_expreso_se_costea_contra_el_expreso(
    crear_orden, crear_ubicacion, tarifario
):
    """
    El caso que motiva los destinos explícitos: el remito dice el exterior, el camión
    descarga en el intermediario y se factura hasta ahí. Sin los explícitos esto es un 422.
    """
    orden = crear_orden(via=Via.TERRESTRE.value, tipo_camion=TipoCamion.SEMI.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL999", pais="UY")],
    )
    expreso = crear_ubicacion("EXP01", tipo=TipoUbicacion.EXPRESO.value, nombre="Expreso")
    OrdenServicioService.replace_destinos(orden, [expreso.id])
    tarifa_por_ubicacion(tarifario, expreso, "92000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("92000.00")
    assert costo.cantidad_destinos == 1
    assert costo.modalidad == ModalidadFlete.DIRECTO.value


def test_los_destinos_explicitos_ganan_sobre_el_puerto_de_la_via(
    crear_orden, crear_ubicacion, puerto, tarifario
):
    orden = crear_orden(via=Via.MARITIMA.value, tipo_camion=TipoCamion.SEMI.value)
    RemitoService.create_remito(
        numero="0001-00000001",
        fecha=None,
        orden_servicio=orden,
        destinos=[crear_ubicacion("CL999", pais="UY")],
    )
    elegido = crear_ubicacion("CL500")
    OrdenServicioService.replace_destinos(orden, [elegido.id])
    tarifa_por_ubicacion(tarifario, puerto, "185000.00", ModalidadFlete.DIRECTO)
    tarifa_por_ubicacion(tarifario, elegido, "77000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("77000.00")


def test_un_destino_explicito_extranjero_no_se_manda_al_puerto(
    crear_orden, crear_ubicacion, puerto, tarifario
):
    """En el camino explícito no hay chequeo de país ni inyección: el humano se hace cargo."""
    orden = crear_orden(via=Via.MARITIMA.value, tipo_camion=TipoCamion.SEMI.value)
    afuera = crear_ubicacion("CL999", pais="UY")
    OrdenServicioService.replace_destinos(orden, [afuera.id])
    tarifa_por_ubicacion(tarifario, puerto, "185000.00", ModalidadFlete.DIRECTO)
    tarifa_por_ubicacion(tarifario, afuera, "50000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("50000.00")


def test_dos_destinos_explicitos_pasan_a_multiparada(crear_orden, crear_ubicacion, tarifario):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    uno = crear_ubicacion("CL501")
    dos = crear_ubicacion("CL502")
    OrdenServicioService.replace_destinos(orden, [uno.id, dos.id])
    tarifa_por_ubicacion(tarifario, uno, "10000.00", ModalidadFlete.DIRECTO)

    with pytest.raises(TarifarioService.TarifaNoResueltaError) as exc:
        CalcularCostoOrdenServicioUseCase.execute(orden.id)

    # Multiparada se resuelve sólo por zona: la tarifa por ubicación no aplica.
    assert exc.value.detail["motivo"] == "sin_zona_comun"


def test_una_camara_ignora_los_destinos_explicitos(crear_orden, crear_ubicacion, transportista):
    orden = crear_orden(
        tipo_operacion=TipoOperacion.CAMARA.value, tipo_camion=TipoCamion.SEMI.value
    )
    OrdenServicioService.replace_destinos(orden, [crear_ubicacion("CL503").id])
    tarifario = TarifarioService.create_tarifario(
        transportista_id=transportista.id, vigente_desde=VIGENTE_DESDE
    )
    concepto = ConceptoAdicional.objects.create(
        codigo="CAM",
        nombre="Cámara",
        unidad=ConceptoUnidadMedida.DIA.value,
        tipo_operacion=TipoOperacion.CAMARA.value,
    )
    TarifaConceptoAdicional.objects.create(
        tarifario=tarifario, concepto=concepto, precio=Decimal("500.00")
    )

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.cantidad_destinos == 0
    assert costo.precio_flete == Decimal("0.00")
    assert costo.modalidad is None
