from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from catalog.dtos import ZonaIn, ZonaOut
from catalog.use_cases import (
    ActualizarZonaUseCase,
    CrearZonaUseCase,
    ListarZonasUseCase,
    ObtenerZonaUseCase,
)
from core.auth import SessionAuth
from shared.dtos import ERRORS
from shared.permisos import PermisoCodigo

zonas_router = Router(tags=["zonas"])


@zonas_router.get(
    "/",
    response={200: list[ZonaOut], **ERRORS},
    auth=SessionAuth(PermisoCodigo.ZONAS_VER),
    summary="Lista las zonas activas",
    operation_id="listarZonas",
)
def listar_zonas(request: HttpRequest):
    return 200, ListarZonasUseCase.execute()


@zonas_router.post(
    "/",
    response={201: ZonaOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ZONAS_CREAR),
    summary="Crea una zona",
    operation_id="crearZona",
)
def crear_zona(request: HttpRequest, payload: ZonaIn):
    return 201, CrearZonaUseCase.execute(payload)


@zonas_router.get(
    "/{int:zona_id}",
    response={200: ZonaOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ZONAS_VER),
    summary="Obtiene una zona",
    operation_id="obtenerZona",
)
def obtener_zona(request: HttpRequest, zona_id: int):
    return 200, ObtenerZonaUseCase.execute(zona_id)


@zonas_router.put(
    "/{int:zona_id}",
    response={200: ZonaOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ZONAS_EDITAR),
    summary="Reemplaza nombre y geometría de una zona",
    operation_id="actualizarZona",
)
def actualizar_zona(request: HttpRequest, zona_id: int, payload: ZonaIn):
    return 200, ActualizarZonaUseCase.execute(zona_id, payload)
