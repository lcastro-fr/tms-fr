from __future__ import annotations

from datetime import datetime

from logistica.models import OrdenServicio
from shared.exceptions import NotFoundError
from transportista.enums import TipoOperacion


class OrdenServicioService:
    class OrdenServicioNotFoundError(NotFoundError):
        pass

    @staticmethod
    def create_orden_servicio(
        origen_id: int,
        transportista_id: int,
        fecha_viaje: datetime | None = None,
        tipo_operacion: str = TipoOperacion.CARGA.value,
        tipo_camion: str | None = None,
        hombreador: bool = False,
    ) -> OrdenServicio:
        return OrdenServicio.objects.create(
            origen_id=origen_id,
            transportista_id=transportista_id,
            fecha_viaje=fecha_viaje,
            tipo_operacion=tipo_operacion,
            tipo_camion=tipo_camion,
            hombreador=hombreador,
        )

    @staticmethod
    def get_orden_servicio(orden_servicio_id: int) -> OrdenServicio | None:
        return OrdenServicio.objects.filter(pk=orden_servicio_id).first()

    @staticmethod
    def get_orden_servicio_or_raise(orden_servicio_id: int) -> OrdenServicio:
        orden_servicio = OrdenServicioService.get_orden_servicio(orden_servicio_id)
        if orden_servicio is None:
            raise OrdenServicioService.OrdenServicioNotFoundError(
                f"No existe la orden de servicio {orden_servicio_id}",
                detail={"orden_servicio_id": orden_servicio_id},
            )
        return orden_servicio
