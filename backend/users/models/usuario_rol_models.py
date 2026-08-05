from __future__ import annotations

from django.conf import settings
from django.db import models

from shared.models import BaseModel
from users.models.rol_models import Rol


class UsuarioRol(BaseModel):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usuario_roles"
    )
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="usuario_roles")

    class Meta(BaseModel.Meta):
        db_table = "usuario_rol"
        verbose_name = "rol del usuario"
        verbose_name_plural = "roles del usuario"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "rol"],
                condition=models.Q(active=True),
                name="uq_usuario_rol_active",
            )
        ]

    def __str__(self) -> str:
        return f"{self.usuario_id} → {self.rol_id}"
