from __future__ import annotations

from django.http import HttpRequest
from django.middleware.csrf import get_token

from users.dtos import LoginIn, SesionOut
from users.services import AutenticacionService, PermisoService


class IniciarSesionUseCase:
    @staticmethod
    def execute(request: HttpRequest, data: LoginIn) -> SesionOut:
        user = AutenticacionService.iniciar_sesion(request, data.email, data.password)
        return SesionOut.from_model(
            user=user,
            roles=PermisoService.nombres_de_roles(user),
            permisos=PermisoService.codigos_de_usuario(user),
            csrf_token=get_token(request),
        )
