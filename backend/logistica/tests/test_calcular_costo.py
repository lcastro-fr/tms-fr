from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon

from catalog.enums import SRID_WGS84, TipoCamion, TipoUbicacion
from catalog.models import Zona
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


def tarifa_por_zona(tarifario, zona, precio: str, modalidad: ModalidadFlete):
    return TarifaFlete.objects.create(
        tarifario=tarifario,
        zona=zona,
        modalidad=modalidad.value,
        tipo_camion=TipoCamion.SEMI.value,
        hombreador=False,
        precio=Decimal(precio),
    )


def zona_cuadrada(nombre: str, lado: float) -> Zona:
    """Un cuadrado centrado en el destino que crea `crear_ubicacion`."""
    x, y = -58.3816, -34.6037
    mitad = lado / 2
    anillo = (
        (x - mitad, y - mitad),
        (x + mitad, y - mitad),
        (x + mitad, y + mitad),
        (x - mitad, y + mitad),
        (x - mitad, y - mitad),
    )
    return Zona.objects.create(
        nombre=nombre, geom=MultiPolygon(Polygon(anillo), srid=SRID_WGS84)
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


def test_recalcular_no_pisa_el_costo_real_cargado_a_mano(crear_orden, crear_ubicacion, tarifario):
    """Es la razón de que costo_real viva en OrdenServicio y no en CostoOrdenServicio."""
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    destino = crear_ubicacion("CL600")
    OrdenServicioService.replace_destinos(orden, [destino.id])
    tarifa_por_ubicacion(tarifario, destino, "92000.00", ModalidadFlete.DIRECTO)
    orden.costo_real = Decimal("99000.00")
    orden.observaciones = "Se pagó el adicional de descarga"
    orden.save(update_fields=["costo_real", "observaciones"])

    CalcularCostoOrdenServicioUseCase.execute(orden.id)
    CalcularCostoOrdenServicioUseCase.execute(orden.id)

    orden.refresh_from_db()
    assert orden.costo_real == Decimal("99000.00")
    assert orden.observaciones == "Se pagó el adicional de descarga"


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


def test_entre_dos_zonas_que_cubren_los_destinos_gana_la_mas_chica(
    crear_orden, crear_ubicacion, tarifario
):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    uno = crear_ubicacion("CL520")
    dos = crear_ubicacion("CL521")
    OrdenServicioService.replace_destinos(orden, [uno.id, dos.id])
    multiparada = ModalidadFlete.MULTIPARADA
    tarifa_por_zona(tarifario, zona_cuadrada("Grande", 1.0), "200000.00", multiparada)
    tarifa_por_zona(tarifario, zona_cuadrada("Chica", 0.2), "80000.00", multiparada)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("80000.00")
    assert costo.modalidad == ModalidadFlete.MULTIPARADA.value


def test_dos_zonas_de_la_misma_superficie_siguen_siendo_ambiguas(
    crear_orden, crear_ubicacion, tarifario
):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value)
    OrdenServicioService.replace_destinos(orden, [crear_ubicacion("CL522").id])
    tarifa_por_zona(tarifario, zona_cuadrada("Una", 0.4), "80000.00", ModalidadFlete.DIRECTO)
    tarifa_por_zona(tarifario, zona_cuadrada("Otra", 0.4), "90000.00", ModalidadFlete.DIRECTO)

    with pytest.raises(TarifarioService.TarifaAmbiguaError) as exc:
        CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert exc.value.detail["zonas"] == ["Una", "Otra"]


def test_override_multiparada_fuerza_la_zona_con_un_solo_destino(
    crear_orden, crear_ubicacion, tarifario
):
    """Con el override, la modalidad la fija el usuario y no la cantidad de destinos."""
    orden = crear_orden(
        tipo_camion=TipoCamion.SEMI.value, modalidad=ModalidadFlete.MULTIPARADA.value
    )
    destino = crear_ubicacion("CL510")
    OrdenServicioService.replace_destinos(orden, [destino.id])
    # Sin el override, un solo destino se costearía contra esta tarifa puntual directo.
    tarifa_por_ubicacion(tarifario, destino, "60000.00", ModalidadFlete.DIRECTO)

    with pytest.raises(TarifarioService.TarifaNoResueltaError) as exc:
        CalcularCostoOrdenServicioUseCase.execute(orden.id)

    # Multiparada se resuelve sólo por zona: la tarifa puntual no aplica.
    assert exc.value.detail["motivo"] == "sin_zona_comun"


def test_override_directo_toma_la_tarifa_puntual_con_dos_destinos(
    crear_orden, crear_ubicacion, tarifario
):
    orden = crear_orden(tipo_camion=TipoCamion.SEMI.value, modalidad=ModalidadFlete.DIRECTO.value)
    uno = crear_ubicacion("CL511")
    dos = crear_ubicacion("CL512")
    OrdenServicioService.replace_destinos(orden, [uno.id, dos.id])
    # Sin el override, dos destinos irían por zona y esta puntual no aplicaría.
    tarifa_por_ubicacion(tarifario, uno, "70000.00", ModalidadFlete.DIRECTO)

    costo = CalcularCostoOrdenServicioUseCase.execute(orden.id)

    assert costo.precio_flete == Decimal("70000.00")
    assert costo.modalidad == ModalidadFlete.DIRECTO.value
    assert costo.cantidad_destinos == 2


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
