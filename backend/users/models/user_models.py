from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models

from users.managers import CustomUserManager
from users.models.rol_models import Rol


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(
        Rol,
        through="users.UsuarioRol",
        related_name="usuarios",
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # type: ignore[misc,assignment]

    def __str__(self) -> str:
        return self.email
