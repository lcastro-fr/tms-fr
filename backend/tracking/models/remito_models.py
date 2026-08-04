from __future__ import annotations

from django.db import models

from catalog.models import Ubicacion
from logistica.models import OrdenServicio
from shared.models import BaseModel


class Remito(BaseModel):
    id = models.BigAutoField(primary_key=True)
    numero = models.CharField(max_length=13)
    fecha = models.DateTimeField(null=True, blank=True)
    orden_servicio = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="remitos"
    )

    class Meta(BaseModel.Meta):
        db_table = "remito"
        verbose_name = "Remito"
        verbose_name_plural = "Remitos"
        constraints = [
            models.UniqueConstraint(
                fields=["numero"],
                condition=models.Q(active=True),
                name="uq_remito_numero_active",
            )
        ]

    def __str__(self) -> str:
        return f"Remito {self.numero}"


class RemitoDestino(BaseModel):
    id = models.BigAutoField(primary_key=True)
    remito = models.ForeignKey(Remito, on_delete=models.CASCADE, related_name="destinos")
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="remitos_destino"
    )

    class Meta(BaseModel.Meta):
        db_table = "remito_destino"
        verbose_name = "Remito Destino"
        verbose_name_plural = "Remitos Destino"
        constraints = [
            models.UniqueConstraint(
                fields=["remito", "ubicacion"],
                condition=models.Q(active=True),
                name="uq_remito_destino_active",
            )
        ]
