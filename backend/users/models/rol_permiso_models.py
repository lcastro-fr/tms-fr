from __future__ import annotations

from django.db import models

from shared.models import BaseModel
from users.models.permiso_models import Permiso
from users.models.rol_models import Rol


class RolPermiso(BaseModel):
    id = models.BigAutoField(primary_key=True)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="rol_permisos")
    permiso = models.ForeignKey(
        Permiso, on_delete=models.CASCADE, related_name="rol_permisos"
    )

    class Meta(BaseModel.Meta):
        db_table = "rol_permiso"
        verbose_name = "permiso del rol"
        verbose_name_plural = "permisos del rol"
        constraints = [
            models.UniqueConstraint(
                fields=["rol", "permiso"],
                condition=models.Q(active=True),
                name="uq_rol_permiso_active",
            )
        ]

    def __str__(self) -> str:
        return f"{self.rol_id} → {self.permiso_id}"
