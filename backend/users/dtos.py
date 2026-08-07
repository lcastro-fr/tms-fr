from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, Field, StringConstraints

from shared.permisos import PermisoCodigo

if TYPE_CHECKING:
    from users.models import User

Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1)


class CsrfOut(BaseModel):
    csrf_token: str


class SesionOut(BaseModel):
    id: int
    email: str
    nombre: str
    is_superuser: bool
    roles: list[str]
    permisos: list[PermisoCodigo]
    csrf_token: str

    @classmethod
    def from_model(
        cls,
        user: User,
        roles: list[str],
        permisos: set[str],
        csrf_token: str,
    ) -> SesionOut:
        return cls(
            id=user.pk,
            email=user.email,
            nombre=user.get_full_name() or user.email,
            is_superuser=user.is_superuser,
            roles=roles,
            permisos=sorted(PermisoCodigo(p) for p in permisos),
            csrf_token=csrf_token,
        )
