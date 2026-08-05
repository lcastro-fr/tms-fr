from __future__ import annotations

from django.http import HttpRequest

from users.services import AutenticacionService


class CerrarSesionUseCase:
    @staticmethod
    def execute(request: HttpRequest) -> None:
        AutenticacionService.cerrar_sesion(request)
