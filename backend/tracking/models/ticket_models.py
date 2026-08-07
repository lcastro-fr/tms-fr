from __future__ import annotations

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from catalog.models import Ubicacion
from logistica.models import OrdenServicio
from shared.models import BaseModel


class Ticket(BaseModel):
    id = models.BigAutoField(primary_key=True)
    numero = models.CharField(max_length=20)
    planta = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="tickets")
    orden_servicio = models.ForeignKey(
        OrdenServicio, on_delete=models.PROTECT, related_name="tickets"
    )
    fecha_ingreso = models.DateTimeField()
    fecha_egreso = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "ticket"
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ["-fecha_ingreso"]
        constraints = [
            models.UniqueConstraint(
                fields=["numero", "planta"],
                name="uq_ticket_numero_planta_active",
                condition=models.Q(active=True),
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_egreso__isnull=True)
                | models.Q(fecha_egreso__gte=models.F("fecha_ingreso")),
                name="ck_ticket_egreso_posterior_a_ingreso",
            ),
        ]
        indexes = [
            GinIndex(
                fields=["numero"],
                name="idx_ticket_numero_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Ticket {self.numero}"
