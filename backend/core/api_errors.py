from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, ValidationError

from shared.exceptions import DomainError

logger = logging.getLogger(__name__)


def _body(code: str, message: str, detail: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def register_exception_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(DomainError)
    def domain_error(request: HttpRequest, exc: DomainError):
        return api.create_response(
            request,
            _body(exc.code, exc.message, exc.detail),
            status=exc.status_code,
        )

    @api.exception_handler(ValidationError)
    def payload_invalid(request: HttpRequest, exc: ValidationError):
        return api.create_response(
            request,
            _body("payload_invalid", "El payload no es válido.", {"errors": exc.errors}),
            status=422,
        )

    @api.exception_handler(AuthenticationError)
    def unauthorized(request: HttpRequest, exc: AuthenticationError):
        return api.create_response(
            request,
            _body("unauthorized", "Credenciales inválidas o ausentes."),
            status=401,
        )

    @api.exception_handler(Http404)
    def not_found(request: HttpRequest, exc: Http404):
        return api.create_response(
            request,
            _body("not_found", str(exc) or "No encontrado."),
            status=404,
        )

    @api.exception_handler(Exception)
    def unhandled(request: HttpRequest, exc: Exception):
        logger.exception("Error no manejado en %s %s", request.method, request.path)
        if settings.DEBUG:
            raise exc
        return api.create_response(
            request,
            _body("internal_error", "Error interno del servidor."),
            status=500,
        )
