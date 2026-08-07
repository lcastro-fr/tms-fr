from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest

from shared.exceptions import DomainError
from users.models import User


class AutenticacionService:
    class CredencialesInvalidasError(DomainError):
        status_code = 401
        code = "unauthorized"

    @staticmethod
    def iniciar_sesion(request: HttpRequest, email: str, password: str) -> User:
        user = authenticate(request, username=email, password=password)
        if user is None:
            raise AutenticacionService.CredencialesInvalidasError("Email o contraseña incorrectos.")
        login(request, user)
        return user

    @staticmethod
    def cerrar_sesion(request: HttpRequest) -> None:
        logout(request)
