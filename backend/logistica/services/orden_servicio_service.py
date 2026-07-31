from __future__ import annotations

from logistica.models import OrdenServicio


class OrdenServicioService:
    @staticmethod
    def create_orden_servicio(
        origen_id: int, transportista_id: int
    ) -> OrdenServicio:
        return OrdenServicio.objects.create(
            origen_id=origen_id, transportista_id=transportista_id
        )
