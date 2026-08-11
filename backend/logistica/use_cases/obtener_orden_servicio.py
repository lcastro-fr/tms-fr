from __future__ import annotations

from logistica.dtos import OrdenServicioDetalleOut, TicketOut
from logistica.enums import OrigenDestinos
from logistica.services import CostoOrdenServicioService, OrdenServicioService
from tracking.services import RemitoService, TicketService


class ObtenerOrdenServicioUseCase:
    @staticmethod
    def execute(orden_servicio_id: int) -> OrdenServicioDetalleOut:
        orden = OrdenServicioService.get_orden_servicio_or_raise(orden_servicio_id)
        tickets = TicketService.list_by_ordenes_servicio([orden.id]).get(orden.id, [])
        remitos = RemitoService.list_by_orden_servicio(orden.id)
        destinos = OrdenServicioService.list_destinos_ubicaciones(orden.id)

        sugeridos = list(
            dict.fromkeys(d.ubicacion for _, destinos_remito in remitos for d in destinos_remito)
        )
        origen = OrigenDestinos.para(orden.tipo_operacion, bool(destinos))

        costo = CostoOrdenServicioService.get_costo_vigente(orden.id)
        return OrdenServicioDetalleOut.from_model(
            orden,
            costo=costo,
            tickets=[TicketOut.from_model(t, TicketService.dias_estadia(t)) for t in tickets],
            costo_desactualizado=CostoOrdenServicioService.esta_desactualizado(
                costo, orden, len(destinos) if destinos else None
            ),
            remitos=remitos,
            destinos=destinos,
            destinos_sugeridos=sugeridos,
            origen_destinos=origen.value,
        )
