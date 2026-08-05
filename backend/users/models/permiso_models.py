from __future__ import annotations

from django.db import models

from shared.models import BaseModel
from shared.permisos import PERMISO_CHOICES


class Permiso(BaseModel):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=60, choices=PERMISO_CHOICES)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "permiso"
        verbose_name = "permiso"
        verbose_name_plural = "permisos"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=models.Q(active=True),
                name="uq_permiso_codigo_active",
            )
        ]

    def __str__(self) -> str:
        return self.codigo
