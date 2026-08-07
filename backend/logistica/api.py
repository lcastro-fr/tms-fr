from __future__ import annotations

from django.http import HttpRequest
from ninja import Query, Router

from core.auth import SessionAuth
from logistica.dtos import (
    OrdenesServicioFilters,
    OrdenServicioDetalleOut,
    OrdenServicioIn,
    OrdenServicioOpcionesOut,
    OrdenServicioOut,
)
from logistica.use_cases import (
    ActualizarOrdenServicioUseCase,
    ListarOrdenesServicioUseCase,
    ObtenerOrdenServicioUseCase,
    OpcionesOrdenServicioUseCase,
)
from shared.dtos import ERRORS
from shared.permisos import PermisoCodigo

ordenes_servicio_router = Router(tags=["ordenes de servicio"])


@ordenes_servicio_router.get(
    "/opciones",
    response={200: OrdenServicioOpcionesOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ORDENES_SERVICIO_VER),
    summary="Valores posibles de tipo de operación, tipo de camión y vía",
    operation_id="opcionesOrdenServicio",
)
def opciones_orden_servicio(request: HttpRequest):
    return 200, OpcionesOrdenServicioUseCase.execute()


@ordenes_servicio_router.get(
    "/",
    response={200: list[OrdenServicioOut], **ERRORS},
    auth=SessionAuth(PermisoCodigo.ORDENES_SERVICIO_VER),
    summary="Lista las órdenes de servicio activas con su costo vigente",
    operation_id="listarOrdenesServicio",
)
def listar_ordenes_servicio(request: HttpRequest, filters: Query[OrdenesServicioFilters]):
    return 200, ListarOrdenesServicioUseCase.execute(filters)


@ordenes_servicio_router.get(
    "/{int:orden_servicio_id}",
    response={200: OrdenServicioDetalleOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ORDENES_SERVICIO_VER),
    summary="Obtiene una orden de servicio con su costo, sus tickets y sus remitos",
    operation_id="obtenerOrdenServicio",
)
def obtener_orden_servicio(request: HttpRequest, orden_servicio_id: int):
    return 200, ObtenerOrdenServicioUseCase.execute(orden_servicio_id)


@ordenes_servicio_router.put(
    "/{int:orden_servicio_id}",
    response={200: OrdenServicioOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ORDENES_SERVICIO_EDITAR),
    summary="Corrige los datos de planificación de una orden de servicio",
    description=(
        "No recalcula el costo: el costo vigente que devuelve puede haber quedado viejo "
        "respecto de los datos nuevos."
    ),
    operation_id="actualizarOrdenServicio",
)
def actualizar_orden_servicio(
    request: HttpRequest, orden_servicio_id: int, payload: OrdenServicioIn
):
    return 200, ActualizarOrdenServicioUseCase.execute(orden_servicio_id, payload)
