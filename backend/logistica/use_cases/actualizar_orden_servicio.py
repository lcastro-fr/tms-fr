from __future__ import annotations

from django.db import transaction

from logistica.dtos import OrdenServicioIn, OrdenServicioOut, TicketOut
from logistica.services import CostoOrdenServicioService, OrdenServicioService
from tracking.services import TicketService


class ActualizarOrdenServicioUseCase:
    @staticmethod
    @transaction.atomic
    def execute(orden_servicio_id: int, data: OrdenServicioIn) -> OrdenServicioOut:
        orden = OrdenServicioService.get_orden_servicio_or_raise(orden_servicio_id)
        orden = OrdenServicioService.update_orden_servicio(
            orden,
            fecha_viaje=data.fecha_viaje,
            tipo_operacion=data.tipo_operacion.value,
            tipo_camion=data.tipo_camion.value if data.tipo_camion else None,
            via=data.via.value,
            hombreador=data.hombreador,
            facturable=data.facturable,
        )
        tickets = TicketService.list_by_ordenes_servicio([orden.id]).get(orden.id, [])
        return OrdenServicioOut.from_model(
            orden,
            costo=CostoOrdenServicioService.get_costo_vigente(orden.id),
            tickets=[TicketOut.from_model(t, TicketService.dias_estadia(t)) for t in tickets],
        )
