from __future__ import annotations

from django.db import models

from catalog.models import Ubicacion
from shared.models import BaseModel
from transportista.models import Transportista


class OrdenServicio(BaseModel):
    id = models.BigAutoField(primary_key=True)
    origen = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="ordenes_servicio"
    )
    transportista = models.ForeignKey(
        Transportista, on_delete=models.PROTECT, related_name="ordenes_servicio"
    )

    class Meta(BaseModel.Meta):
        db_table = "orden_servicio"
        verbose_name = "Orden de Servicio"
        verbose_name_plural = "Ordenes de Servicio"

    def __str__(self) -> str:
        return f"OS {self.id}"
