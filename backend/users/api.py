from __future__ import annotations

from django.http import HttpRequest
from ninja import Router
from ninja.utils import check_csrf

from core.auth import SessionAuth, current_user
from shared.dtos import ERRORS
from shared.exceptions import ForbiddenError
from users.dtos import CsrfOut, LoginIn, SesionOut
from users.use_cases import (
    CerrarSesionUseCase,
    IniciarSesionUseCase,
    ObtenerCsrfUseCase,
    ObtenerSesionUseCase,
)

auth_router = Router(tags=["auth"])


@auth_router.get(
    "/csrf",
    response={200: CsrfOut, **ERRORS},
    auth=None,
    summary="Entrega un token de CSRF para poder loguearse",
    operation_id="obtenerCsrf",
)
def obtener_csrf(request: HttpRequest):
    return 200, ObtenerCsrfUseCase.execute(request)


@auth_router.post(
    "/login",
    response={200: SesionOut, **ERRORS},
    auth=None,
    summary="Inicia sesión con email y contraseña",
    operation_id="login",
)
def login(request: HttpRequest, payload: LoginIn):
    if check_csrf(request) is not None:
        raise ForbiddenError("Falló la validación de CSRF.")
    return 200, IniciarSesionUseCase.execute(request, payload)


@auth_router.post(
    "/logout",
    response={204: None, **ERRORS},
    auth=SessionAuth(),
    summary="Cierra la sesión",
    operation_id="logout",
)
def logout(request: HttpRequest):
    CerrarSesionUseCase.execute(request)
    return 204, None


@auth_router.get(
    "/me",
    response={200: SesionOut, **ERRORS},
    auth=SessionAuth(),
    summary="Devuelve la sesión actual con sus permisos",
    operation_id="obtenerSesion",
)
def obtener_sesion(request: HttpRequest):
    return 200, ObtenerSesionUseCase.execute(request, current_user(request))
