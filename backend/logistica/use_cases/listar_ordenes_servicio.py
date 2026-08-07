from __future__ import annotations

from logistica.dtos import OrdenesServicioFilters, OrdenServicioOut, TicketOut
from logistica.services import CostoOrdenServicioService, OrdenServicioService
from tracking.services import TicketService


class ListarOrdenesServicioUseCase:
    @staticmethod
    def execute(filters: OrdenesServicioFilters) -> list[OrdenServicioOut]:
        ordenes = OrdenServicioService.list_ordenes_servicio(
            facturable=filters.facturable,
            con_costo=filters.con_costo,
            numero=filters.numero,
            fecha_viaje_desde=filters.fecha_viaje_desde,
            fecha_viaje_hasta=filters.fecha_viaje_hasta,
            incluir_sin_fecha=filters.incluir_sin_fecha,
        )
        ids = [orden.id for orden in ordenes]
        costos = CostoOrdenServicioService.get_costos_vigentes(ids)
        tickets = TicketService.list_by_ordenes_servicio(ids)
        return [
            OrdenServicioOut.from_model(
                orden,
                costos.get(orden.id),
                [
                    TicketOut.from_model(t, TicketService.dias_estadia(t))
                    for t in tickets.get(orden.id, [])
                ],
            )
            for orden in ordenes
        ]
