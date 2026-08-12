from __future__ import annotations

from django.contrib.gis.db import models

from shared.models import BaseModel


class DivisionPolitica(BaseModel):
    nombre = models.CharField(max_length=80)
    superficie_km2 = models.DecimalField(max_digits=12, decimal_places=4)
    geom = models.MultiPolygonField(srid=4326)
    geom_display = models.MultiPolygonField(srid=4326)

    class Meta(BaseModel.Meta):
        abstract = True

    def __str__(self) -> str:
        return self.nombre


class Provincia(DivisionPolitica):
    codigo = models.CharField(max_length=2, primary_key=True)

    class Meta(DivisionPolitica.Meta):
        db_table = "provincia"
        verbose_name = "provincia"
        verbose_name_plural = "provincias"
        ordering = ["nombre"]


class Departamento(DivisionPolitica):
    codigo = models.CharField(max_length=5, primary_key=True)
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name="departamentos")

    class Meta(DivisionPolitica.Meta):
        db_table = "departamento"
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        ordering = ["nombre"]
