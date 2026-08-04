from __future__ import annotations

from django.db import models

from catalog.enums import TIPO_CAMION_CHOICES
from catalog.models import Ubicacion
from shared.models import BaseModel
from transportista.enums import TIPO_OPERACION_CHOICES, TipoOperacion
from transportista.models import Transportista


class OrdenServicio(BaseModel):
    id = models.BigAutoField(primary_key=True)
    origen = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="ordenes_servicio")
    fecha_viaje = models.DateTimeField(null=True, blank=True)
    transportista = models.ForeignKey(
        Transportista, on_delete=models.PROTECT, related_name="ordenes_servicio"
    )
    tipo_operacion = models.CharField(
        max_length=20, choices=TIPO_OPERACION_CHOICES, default=TipoOperacion.CARGA.value
    )
    tipo_camion = models.CharField(  # noqa: DJ001
        max_length=20, choices=TIPO_CAMION_CHOICES, null=True, blank=True
    )
    hombreador = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = "orden_servicio"
        verbose_name = "Orden de Servicio"
        verbose_name_plural = "Ordenes de Servicio"

    def __str__(self) -> str:
        return f"OS {self.id}"
