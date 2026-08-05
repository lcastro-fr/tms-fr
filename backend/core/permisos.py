from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.http import HttpRequest

from users.services import PermisoService

if TYPE_CHECKING:
    from users.models import User


def get_user_permissions(request: HttpRequest, user: User) -> set[str]:
    """Memoizado por request: una operación puede chequear más de un código."""
    cacheado = getattr(request, "_permisos", None)
    if cacheado is None:
        cacheado = PermisoService.codigos_de_usuario(user)
        request._permisos = cacheado  # type: ignore[attr-defined]
    return cast(set[str], cacheado)
