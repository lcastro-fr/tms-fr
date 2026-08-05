from __future__ import annotations

from django.http import HttpRequest
from django.middleware.csrf import get_token

from users.dtos import SesionOut
from users.models import User
from users.services import PermisoService


class ObtenerSesionUseCase:
    @staticmethod
    def execute(request: HttpRequest, user: User) -> SesionOut:
        return SesionOut.from_model(
            user=user,
            roles=PermisoService.nombres_de_roles(user),
            permisos=PermisoService.codigos_de_usuario(user),
            csrf_token=get_token(request),
        )
