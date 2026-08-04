from __future__ import annotations

from django.db import models

from shared.models import BaseModel
from transportista.enums import (
    MODALIDAD_FLETE_CHOICES,
    TIPO_OPERACION_CHOICES,
)
from transportista.models import TarifaConceptoAdicional, TarifaFlete

from .orden_servicio_models import OrdenServicio


class CostoOrdenServicio(BaseModel):
    id = models.BigAutoField(primary_key=True)
    orden_servicio = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="costos"
    )
    tarifa_flete = models.ForeignKey(
        TarifaFlete, on_delete=models.PROTECT, related_name="costos", null=True, blank=True
    )
    precio_flete = models.DecimalField(max_digits=14, decimal_places=2)
    tarifa_concepto = models.ForeignKey(
        TarifaConceptoAdicional,
        on_delete=models.PROTECT,
        related_name="costos",
        null=True,
        blank=True,
    )
    dias = models.PositiveIntegerField()
    precio_dia = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # Metadata
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OPERACION_CHOICES)
    modalidad = models.CharField(  # noqa: DJ001
        max_length=20, choices=MODALIDAD_FLETE_CHOICES, null=True, blank=True
    )
    tipo_camion = models.CharField(max_length=20, null=True, blank=True)  # noqa: DJ001
    hombreador = models.BooleanField()
    cantidad_destinos = models.PositiveIntegerField()
    fecha_viaje = models.DateTimeField()

    class Meta(BaseModel.Meta):
        db_table = "costo_orden_servicio"
        verbose_name = "Costo de Orden de Servicio"
        verbose_name_plural = "Costos de Ordenes de Servicio"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["orden_servicio"],
                name="uq_costo_orden_servicio_active",
                condition=models.Q(active=True),
            )
        ]

    @property
    def subtotal_adicional(self):
        if self.precio_dia is None:
            return 0
        return self.dias * self.precio_dia

    @property
    def total(self):
        return self.precio_flete + self.subtotal_adicional

    def __str__(self) -> str:
        return f"Costo OS {self.orden_servicio_id}: {self.total}"
