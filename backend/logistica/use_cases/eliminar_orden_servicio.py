from __future__ import annotations

from logistica.services import OrdenServicioService


class EliminarOrdenServicioUseCase:
    @staticmethod
    def execute(orden_servicio_id: int) -> None:
        orden_servicio = OrdenServicioService.get_orden_servicio_or_raise(orden_servicio_id)
        OrdenServicioService.delete_orden_servicio(orden_servicio)
