from __future__ import annotations

from typing import Any

import pytest

from lib.routing.domain import Coordinate, GeocodeQuery, Geocoder, RoutingError
from shared.permisos import PermisoCodigo
from users.models import Permiso, Rol, RolPermiso, User, UsuarioRol
from users.services import PermisoService

PASSWORD = "test-pass-1234"


class GeocoderFalso(Geocoder):
    """Sin coordenada levanta el error que se le pase; `consultas` registra las llamadas."""

    def __init__(self, coordinate: Coordinate | None = None, error: RoutingError | None = None):
        self.coordinate = coordinate
        self.error = error or RoutingError("sin resultados")
        self.consultas: list[GeocodeQuery] = []

    def geocode(self, query: GeocodeQuery) -> Coordinate:
        self.consultas.append(query)
        if self.coordinate is None:
            raise self.error
        return self.coordinate


@pytest.fixture
def geocoder_falso():
    return GeocoderFalso


@pytest.fixture
def password() -> str:
    return PASSWORD


@pytest.fixture
def permisos(db: Any) -> dict[str, Permiso]:
    PermisoService.sincronizar()
    return {p.codigo: p for p in Permiso.objects.all()}


@pytest.fixture
def crear_usuario(db: Any):
    def _crear(email: str = "user@tms.test", **extra: Any) -> User:
        return User.objects.create_user(email=email, password=PASSWORD, **extra)

    return _crear


@pytest.fixture
def crear_rol(db: Any, permisos: dict[str, Permiso]):
    def _crear(nombre: str, *codigos: PermisoCodigo) -> Rol:
        rol = Rol.objects.create(nombre=nombre)
        for codigo in codigos:
            RolPermiso.objects.create(rol=rol, permiso=permisos[codigo.value])
        return rol

    return _crear


@pytest.fixture
def asignar_rol(db: Any):
    def _asignar(user: User, rol: Rol) -> UsuarioRol:
        return UsuarioRol.objects.create(usuario=user, rol=rol)

    return _asignar
