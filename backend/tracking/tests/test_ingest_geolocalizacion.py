from __future__ import annotations

import pytest
from django.contrib.gis.geos import Point

from catalog.enums import PAIS_LOCAL, SRID_WGS84
from catalog.models import Ubicacion
from routing.domain.exceptions import RoutingError
from routing.domain.ports import Geocoder
from routing.domain.values import Coordinate, GeocodeQuery
from routing.factory import GeocoderNoConfigurado, build_geocoder
from tracking.dtos import TicketIngestIn
from tracking.use_cases import IngestTicketUseCase

pytestmark = pytest.mark.django_db

INGEST = "/api/v1/tickets/ingest"


class GeocoderFalso(Geocoder):
    def __init__(self, coordinate: Coordinate | None = None):
        self.coordinate = coordinate
        self.consultas: list[GeocodeQuery] = []

    def geocode(self, query: GeocodeQuery) -> Coordinate:
        self.consultas.append(query)
        if self.coordinate is None:
            raise RoutingError("sin resultados")
        return self.coordinate


@pytest.fixture
def planta(db):
    return Ubicacion.objects.create(
        codigo="PL01",
        tipo="planta",
        nombre="Planta Rosario",
        calle="Ruta 9 km 1",
        localidad="Rosario",
        provincia="Santa Fe",
        coordinates=Point(-60.6393, -32.9468, srid=SRID_WGS84),
    )


def payload(codigo_destino: str = "CL999", pais: str = "Argentina") -> TicketIngestIn:
    return TicketIngestIn.model_validate(
        {
            "numero": "TK-1",
            "planta_codigo": "PL01",
            "fecha_ingreso": "2026-08-06T10:00:00-03:00",
            "transportista": {"cuit": "30-11111111-9", "razon_social": "Fletes SA"},
            "remitos": [
                {
                    "numero": "0001-00000001",
                    "fecha": "2026-08-06T09:00:00-03:00",
                    "destinos": [
                        {
                            "codigo": codigo_destino,
                            "nombre": "Cliente Nuevo",
                            "direccion": "Av. Corrientes 1000",
                            "localidad": "CABA",
                            "provincia": "Buenos Aires",
                            "pais": pais,
                        }
                    ],
                }
            ],
        }
    )


def test_crea_la_ubicacion_faltante_con_la_coordenada_geolocalizada(planta):
    geocoder = GeocoderFalso(Coordinate.from_lnglat(-58.3816, -34.6037))

    IngestTicketUseCase(geocoder).execute(payload())

    ubicacion = Ubicacion.objects.get(codigo="CL999")
    assert ubicacion.validada is False
    assert ubicacion.coordinates is not None
    assert (ubicacion.coordinates.x, ubicacion.coordinates.y) == pytest.approx((-58.3816, -34.6037))


@pytest.mark.parametrize("pais", ["Argentina", "AR", " ar "])
def test_el_pais_se_guarda_canonico(planta, pais):
    IngestTicketUseCase(GeocoderFalso(Coordinate.from_lnglat(-58.3816, -34.6037))).execute(
        payload(pais=pais)
    )

    assert Ubicacion.objects.get(codigo="CL999").pais_id == PAIS_LOCAL


@pytest.mark.parametrize("pais", ["Narnia", "", "Q1"])
def test_un_pais_no_soportado_no_voltea_la_ingesta(planta, pais):
    salida = IngestTicketUseCase(GeocoderFalso(Coordinate.from_lnglat(-58.3816, -34.6037))).execute(
        payload(pais=pais)
    )

    assert salida.remitos_creados == ["0001-00000001"]
    assert Ubicacion.objects.get(codigo="CL999").pais_id is None


@pytest.mark.parametrize("pais", ["Narnia", "", "Q1"])
def test_los_destinos_sin_pais_viajan_en_la_salida(planta, pais):
    salida = IngestTicketUseCase(GeocoderFalso(Coordinate.from_lnglat(-58.3816, -34.6037))).execute(
        payload(pais=pais)
    )

    assert [d.codigo for d in salida.destinos_sin_pais] == ["CL999"]
    assert salida.destinos_sin_pais[0].pais_recibido == pais.strip()
    assert salida.completo is False


def test_el_adapter_rechaza_un_pais_que_no_soporta():
    from routing.adapters import OpenRouteServiceAdapter

    adapter = OpenRouteServiceAdapter(api_key="una-key")
    query = GeocodeQuery(direccion="a", localidad="b", provincia="c", pais="Brasil")

    with pytest.raises(RoutingError, match="no soportado"):
        adapter.geocode(query)


def test_los_destinos_sin_geolocalizar_viajan_en_la_salida(planta):
    salida = IngestTicketUseCase(GeocoderFalso(None)).execute(payload())

    assert [d.codigo for d in salida.destinos_sin_geolocalizar] == ["CL999"]
    assert salida.destinos_sin_geolocalizar[0].motivo
    assert salida.completo is False


def test_si_falla_el_geocoder_la_ubicacion_se_crea_sin_coordenadas(planta):
    salida = IngestTicketUseCase(GeocoderFalso(None)).execute(payload())

    ubicacion = Ubicacion.objects.get(codigo="CL999")
    assert ubicacion.coordinates is None
    assert ubicacion.validada is False
    assert salida.remitos_creados == ["0001-00000001"]


def test_sin_api_key_el_geocoder_degrada_en_vez_de_romper(planta, settings):
    settings.ORS_API_KEY = ""
    geocoder = build_geocoder()
    assert isinstance(geocoder, GeocoderNoConfigurado)

    IngestTicketUseCase(geocoder).execute(payload())

    assert Ubicacion.objects.get(codigo="CL999").coordinates is None


def test_el_endpoint_responde_201(client, planta, settings):
    settings.INGEST_API_KEY = "una-key"
    settings.ORS_API_KEY = ""

    resp = client.post(
        INGEST,
        payload().model_dump(mode="json"),
        content_type="application/json",
        HTTP_X_API_KEY="una-key",
    )

    assert resp.status_code == 201, resp.content
    assert resp.json()["remitos_creados"] == ["0001-00000001"]


def test_no_se_geolocaliza_una_ubicacion_que_ya_existe(planta):
    Ubicacion.objects.create(
        codigo="CL999",
        tipo="cliente",
        nombre="Cliente Existente",
        calle="Otra 1",
        localidad="CABA",
        provincia="Buenos Aires",
    )
    geocoder = GeocoderFalso(Coordinate.from_lnglat(-58.3816, -34.6037))

    IngestTicketUseCase(geocoder).execute(payload())

    assert geocoder.consultas == []
