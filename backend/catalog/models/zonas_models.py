from __future__ import annotations

from django.contrib.gis.db import models

from catalog.db_functions import SuperficieKm2
from shared.models import BaseModel


class Zona(BaseModel):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    geom = models.MultiPolygonField(srid=4326)
    superficie_km2 = models.GeneratedField(
        expression=SuperficieKm2("geom"),
        output_field=models.DecimalField(max_digits=12, decimal_places=4),
        db_persist=True,
    )

    class Meta(BaseModel.Meta):
        db_table = "zona"
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre"],
                condition=models.Q(active=True),
                name="uq_zona_nombre_active",
            )
        ]

    def __str__(self) -> str:
        return self.nombre
