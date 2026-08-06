from __future__ import annotations

from django.db import models

from shared.models import BaseModel


class Pais(BaseModel):
    codigo = models.CharField(max_length=2, primary_key=True)
    nombre = models.CharField(max_length=80)

    class Meta(BaseModel.Meta):
        db_table = "pais"
        verbose_name = "país"
        verbose_name_plural = "países"
        constraints = [
            models.UniqueConstraint(
                fields=["nombre"],
                name="uq_pais_nombre",
                condition=models.Q(active=True),
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo})"
