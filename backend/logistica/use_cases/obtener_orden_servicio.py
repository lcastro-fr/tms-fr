from __future__ import annotations

from logistica.dtos import OrdenServicioDetalleOut, TicketOut
from logistica.services import CostoOrdenServicioService, OrdenServicioService
from tracking.services import RemitoService, TicketService


class ObtenerOrdenServicioUseCase:
    @staticmethod
    def execute(orden_servicio_id: int) -> OrdenServicioDetalleOut:
        orden = OrdenServicioService.get_orden_servicio_or_raise(orden_servicio_id)
        tickets = TicketService.list_by_ordenes_servicio([orden.id]).get(orden.id, [])
        return OrdenServicioDetalleOut.from_model(
            orden,
            costo=CostoOrdenServicioService.get_costo_vigente(orden.id),
            tickets=[TicketOut.from_model(t, TicketService.dias_estadia(t)) for t in tickets],
            remitos=RemitoService.list_by_orden_servicio(orden.id),
        )
