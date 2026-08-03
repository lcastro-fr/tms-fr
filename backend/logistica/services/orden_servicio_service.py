from __future__ import annotations

from logistica.models import OrdenServicio


class OrdenServicioService:
    @staticmethod
    def create_orden_servicio(
        origen_id: int,
        transportista_id: int,
        tipo_camion: str | None = None,
        hombreador: bool = False,
    ) -> OrdenServicio:
        return OrdenServicio.objects.create(
            origen_id=origen_id,
            transportista_id=transportista_id,
            tipo_camion=tipo_camion,
            hombreador=hombreador,
        )

    @staticmethod
    def get_orden_servicio(orden_servicio_id: int) -> OrdenServicio | None:
        return OrdenServicio.objects.filter(pk=orden_servicio_id).first()
