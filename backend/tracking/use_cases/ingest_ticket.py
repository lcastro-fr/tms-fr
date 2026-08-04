from __future__ import annotations

import logging

from django.db import transaction

from catalog.services import UbicacionService
from logistica.services import OrdenServicioService
from tracking.dtos import RemitoOmitidoOut, TicketIngestIn, TicketIngestOut
from tracking.services import RemitoService, TicketService
from transportista.services import TransportistaService

logger = logging.getLogger(__name__)


class IngestTicketUseCase:
    @staticmethod
    @transaction.atomic
    def execute(data: TicketIngestIn) -> TicketIngestOut:
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
            destinos, faltantes = UbicacionService.resolve_codigos(remito.destinos)

            if faltantes:
                motivo = f"Códigos de destino desconocidos: {', '.join(faltantes)}"
                logger.warning("Se omite el remito %s: %s", remito.numero, motivo)
                omitidos.append(RemitoOmitidoOut(numero=remito.numero, motivo=motivo))
                continue

            try:
                RemitoService.create_remito(
                    numero=remito.numero,
                    fecha=remito.fecha,
                    orden_servicio=orden_servicio,
                    destinos=destinos,
                )
            except RemitoService.RemitoAlreadyExistsError as exc:
                logger.warning("Se omite el remito %s: %s", remito.numero, exc.message)
                omitidos.append(
                    RemitoOmitidoOut(numero=remito.numero, motivo=exc.message)
                )
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
