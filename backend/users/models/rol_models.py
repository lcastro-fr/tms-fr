from __future__ import annotations

from django.db import models

from shared.models import BaseModel
from users.models.permiso_models import Permiso


class Rol(BaseModel):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=200, blank=True)
    permisos = models.ManyToManyField(
        Permiso,
        through="users.RolPermiso",
        related_name="roles",
        blank=True,
    )

    class Meta(BaseModel.Meta):
        db_table = "rol"
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre"],
                condition=models.Q(active=True),
                name="uq_rol_nombre_active",
            )
        ]

    def __str__(self) -> str:
        return self.nombre
