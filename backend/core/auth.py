from __future__ import annotations

import hmac
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.http import HttpRequest
from ninja.security import APIKeyHeader
from ninja.security import SessionAuth as NinjaSessionAuth

from core.permisos import get_user_permissions
from shared.exceptions import ForbiddenError
from shared.permisos import PermisoCodigo

if TYPE_CHECKING:
    from users.models import User


class IngestApiKeyAuth(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request: HttpRequest, key: str | None) -> str | None:
        expected = settings.INGEST_API_KEY
        if not key or not expected:
            return None
        if not hmac.compare_digest(key, expected):
            return None
        return "ingest"


class SessionAuth(NinjaSessionAuth):
    """
    Sesión de Django, opcionalmente con los permisos que la operación exige.
    """

    def __init__(self, *codigos: PermisoCodigo) -> None:
        self.requeridos = {c.value for c in codigos}
        super().__init__()

    def authenticate(self, request: HttpRequest, key: str | None) -> Any | None:
        if not request.user.is_authenticated:
            return None

        user = request.user
        if self.requeridos and not self.requeridos & get_user_permissions(request, user):
            raise ForbiddenError(
                "No tenés permiso para esta operación.",
                detail={"requiere": sorted(self.requeridos)},
            )
        return user


def current_user(request: HttpRequest) -> User:
    return cast("User", request.auth)  # type: ignore[attr-defined]
