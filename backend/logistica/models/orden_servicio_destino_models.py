from __future__ import annotations

from django.db import models

from catalog.models import Ubicacion
from logistica.models.orden_servicio_models import OrdenServicio
from shared.models import BaseModel


class OrdenServicioDestino(BaseModel):
    """Hasta dónde se factura el viaje, que no siempre es el destino del remito."""

    id = models.BigAutoField(primary_key=True)
    orden_servicio = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="destinos"
    )
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="ordenes_servicio_destino"
    )
    secuencia = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        db_table = "orden_servicio_destino"
        verbose_name = "Orden Servicio Destino"
        verbose_name_plural = "Ordenes Servicio Destino"
        constraints = [
            models.UniqueConstraint(
                fields=["orden_servicio", "ubicacion"],
                condition=models.Q(active=True),
                name="uq_orden_servicio_destino_active",
            )
        ]

    def __str__(self) -> str:
        return f"OS {self.orden_servicio_id} → {self.ubicacion_id}"
