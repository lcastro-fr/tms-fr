from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.contrib.gis.geos import Point

from catalog.enums import PAIS_LOCAL, SRID_WGS84, DestinoDefault, TipoUbicacion
from catalog.models import Pais, Ubicacion
from logistica.services import OrdenServicioService
from transportista.enums import Via
from transportista.models import Transportista

FECHA_VIAJE = datetime(2026, 8, 6, 13, 0, tzinfo=UTC)


@pytest.fixture
def crear_pais(db):
    def _crear(codigo: str, nombre: str | None = None) -> Pais:
        pais, _ = Pais.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre or f"País {codigo}"}
        )
        return pais

    return _crear


@pytest.fixture
def crear_ubicacion(crear_pais):
    def _crear(
        codigo: str,
        pais: str | None = PAIS_LOCAL,
        lng: float = -58.3816,
        lat: float = -34.6037,
        **extra,
    ) -> Ubicacion:
        return Ubicacion.objects.create(
            codigo=codigo,
            tipo=extra.pop("tipo", TipoUbicacion.CLIENTE.value),
            nombre=extra.pop("nombre", f"Destino {codigo}"),
            calle="Av. Siempreviva 742",
            localidad="CABA",
            provincia="Buenos Aires",
            pais=crear_pais(pais) if pais else None,
            coordinates=Point(lng, lat, srid=SRID_WGS84),
            **extra,
        )

    return _crear


@pytest.fixture
def puerto(crear_ubicacion):
    return crear_ubicacion(
        "ARBUE",
        tipo=TipoUbicacion.PUERTO.value,
        nombre="Puerto de Buenos Aires",
        destino_default=DestinoDefault.PUERTO_MARITIMO.value,
        lng=-58.3700,
        lat=-34.5750,
    )


@pytest.fixture
def aeropuerto(crear_ubicacion):
    return crear_ubicacion(
        "AREZE",
        tipo=TipoUbicacion.AEROPUERTO.value,
        nombre="Aeropuerto de Ezeiza",
        destino_default=DestinoDefault.AEROPUERTO.value,
        lng=-58.5358,
        lat=-34.8222,
    )


@pytest.fixture
def transportista(db):
    return Transportista.objects.create(cuit="30-11111111-9", razon_social="Fletes SA")


@pytest.fixture
def crear_orden(crear_ubicacion, transportista):
    planta: list[Ubicacion] = []

    def _crear(via: str = Via.TERRESTRE.value, **extra):
        if not planta:
            planta.append(crear_ubicacion("PL01", tipo=TipoUbicacion.PLANTA.value, nombre="Planta"))
        origen = planta[0]
        return OrdenServicioService.create_orden_servicio(
            origen_id=origen.id,
            transportista_id=transportista.id,
            fecha_viaje=extra.pop("fecha_viaje", FECHA_VIAJE),
            facturable=extra.pop("facturable", True),
            via=via,
            **extra,
        )

    return _crear
