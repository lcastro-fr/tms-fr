from __future__ import annotations

import logging

from django.db import transaction

from catalog.enums import TipoUbicacion
from catalog.services import UbicacionService
from logistica.services import OrdenServicioService
from routing.domain.exceptions import RoutingError
from routing.domain.ports import Geocoder
from routing.domain.values import Coordinate, GeocodeQuery
from tracking.dtos import RemitoOmitidoOut, RemitoUbicacionIn, TicketIngestIn, TicketIngestOut
from tracking.services import RemitoService, TicketService
from transportista.services import TransportistaService

logger = logging.getLogger(__name__)


class IngestTicketUseCase:
    def __init__(self, geocoder: Geocoder):
        self._geocoder = geocoder

    @transaction.atomic
    def execute(self, data: TicketIngestIn) -> TicketIngestOut:
        transportista = TransportistaService.get_or_create(
            cuit=data.transportista.cuit,
            razon_social=data.transportista.razon_social,
        )
        planta = UbicacionService.get_ubicacion_by_codigo_or_raise(data.planta_codigo)

        orden_servicio = OrdenServicioService.create_orden_servicio(
            origen_id=planta.id,
            transportista_id=transportista.id,
            fecha_viaje=data.fecha_ingreso,
        )

        creados: list[str] = []
        omitidos: list[RemitoOmitidoOut] = []

        for remito in data.remitos:
            destinos_map: dict[str, RemitoUbicacionIn] = {u.codigo: u for u in remito.destinos}
            destinos, faltantes = UbicacionService.resolve_codigos(destinos_map.keys())

            if faltantes:
                for ubicacion in faltantes:
                    destino = destinos_map.get(ubicacion)
                    geocode_query = GeocodeQuery(
                        direccion=destino.direccion,
                        localidad=destino.localidad,
                        provincia=destino.provincia,
                        pais=destino.provincia,
                    )
                    try:
                        coordinates = self._geocoder.geocode(query=geocode_query)
                    except RoutingError:
                        coordinates = None

                    # Geocode query tiene algunos cleans de datos
                    ubicacion_instance, _ = UbicacionService.upsert_by_codigo(
                        codigo=destino.codigo,
                        tipo=TipoUbicacion.CLIENTE,
                        nombre=destino.nombre,
                        calle=geocode_query.direccion,
                        localidad=geocode_query.localidad,
                        provincia=geocode_query.provincia,
                        pais=geocode_query.pais,
                        lat=coordinates.lat if coordinates else None,
                        lng=coordinates.lng if coordinates else None,
                        validada=False,
                    )
                    destinos.append(ubicacion_instance)

            try:
                RemitoService.create_remito(
                    numero=remito.numero,
                    fecha=remito.fecha,
                    orden_servicio=orden_servicio,
                    destinos=destinos,
                )
            except RemitoService.RemitoAlreadyExistsError as exc:
                logger.warning("Se omite el remito %s: %s", remito.numero, exc.message)
                omitidos.append(RemitoOmitidoOut(numero=remito.numero, motivo=exc.message))
                continue

            creados.append(remito.numero)

        ticket = TicketService.create_ticket(
            numero=data.numero,
            planta=planta,
            orden_servicio=orden_servicio,
            fecha_ingreso=data.fecha_ingreso,
            fecha_egreso=data.fecha_egreso,
        )

        return TicketIngestOut.from_model(ticket, creados, omitidos)
