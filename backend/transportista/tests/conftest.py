from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon

from catalog.enums import PAIS_LOCAL, SRID_WGS84, TipoUbicacion
from catalog.models import Pais, Ubicacion, Zona
from logistica.models import CostoOrdenServicio
from logistica.services import OrdenServicioService
from shared.permisos import PermisoCodigo
from transportista.enums import ConceptoUnidadMedida, TipoOperacion, Via
from transportista.models import ConceptoAdicional, Transportista

VIGENTE_DESDE = datetime(2026, 1, 1, tzinfo=UTC)
FECHA_VIAJE = datetime(2026, 8, 6, 13, 0, tzinfo=UTC)

CUADRADO = (
    (-58.5, -34.6),
    (-58.4, -34.6),
    (-58.4, -34.5),
    (-58.5, -34.5),
    (-58.5, -34.6),
)


@pytest.fixture
def usuario_con(crear_usuario, crear_rol, asignar_rol):
    def _crear(*codigos: PermisoCodigo):
        user = crear_usuario()
        asignar_rol(user, crear_rol("rol", *codigos))
        return user

    return _crear


@pytest.fixture
def transportista(db):
    return Transportista.objects.create(cuit="30-11111111-9", razon_social="Fletes SA")


@pytest.fixture
def otro_transportista(db):
    return Transportista.objects.create(cuit="30-22222222-4", razon_social="Camiones SRL")


@pytest.fixture
def zona(db):
    return Zona.objects.create(
        nombre="Norte", geom=MultiPolygon(Polygon(CUADRADO), srid=SRID_WGS84)
    )


@pytest.fixture
def ubicacion(db):
    pais, _ = Pais.objects.get_or_create(codigo=PAIS_LOCAL, defaults={"nombre": "Argentina"})
    return Ubicacion.objects.create(
        codigo="CL100",
        tipo=TipoUbicacion.CLIENTE.value,
        nombre="Cliente 100",
        calle="Av. Siempreviva 742",
        localidad="CABA",
        provincia="Buenos Aires",
        pais=pais,
        coordinates=Point(-58.45, -34.55, srid=SRID_WGS84),
    )


@pytest.fixture
def concepto(db):
    return ConceptoAdicional.objects.create(
        codigo="ESTADIA",
        nombre="Estadía",
        unidad=ConceptoUnidadMedida.DIA.value,
        tipo_operacion=TipoOperacion.CARGA.value,
    )


@pytest.fixture
def costear(db, ubicacion, transportista):
    """Deja una tarifa referenciada por un costo vigente, que es lo que la marca en uso."""

    def _costear(tarifa_flete=None, tarifa_concepto=None) -> CostoOrdenServicio:
        orden = OrdenServicioService.create_orden_servicio(
            origen_id=ubicacion.id,
            transportista_id=transportista.id,
            fecha_viaje=FECHA_VIAJE,
            facturable=True,
            via=Via.TERRESTRE.value,
        )
        return CostoOrdenServicio.objects.create(
            orden_servicio=orden,
            tarifa_flete=tarifa_flete,
            precio_flete=Decimal("185000.00"),
            tarifa_concepto=tarifa_concepto,
            dias=1,
            precio_dia=Decimal("1000.00") if tarifa_concepto else None,
            tipo_operacion=TipoOperacion.CARGA.value,
            hombreador=False,
            cantidad_destinos=1,
            fecha_viaje=FECHA_VIAJE,
        )

    return _costear
