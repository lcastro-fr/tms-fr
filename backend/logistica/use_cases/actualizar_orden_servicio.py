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
            modalidad=data.modalidad.value if data.modalidad else None,
            hombreador=data.hombreador,
            facturable=data.facturable,
            costo_real=data.costo_real,
            observaciones=data.observaciones,
        )
        if data.destinos is not None:
            OrdenServicioService.replace_destinos(orden, [d.ubicacion_id for d in data.destinos])

        destinos = OrdenServicioService.list_destinos(orden.id)
        tickets = TicketService.list_by_ordenes_servicio([orden.id]).get(orden.id, [])
        costo = CostoOrdenServicioService.get_costo_vigente(orden.id)
        return OrdenServicioOut.from_model(
            orden,
            costo=costo,
            tickets=[TicketOut.from_model(t, TicketService.dias_estadia(t)) for t in tickets],
            costo_desactualizado=CostoOrdenServicioService.esta_desactualizado(
                costo, orden, len(destinos) if destinos else None
            ),
        )
