from __future__ import annotations

from django.http import HttpRequest
from ninja import Query, Router

from core.auth import SessionAuth
from shared.dtos import ERRORS
from shared.permisos import PermisoCodigo
from transportista.dtos import (
    CerrarTarifarioIn,
    TarifarioDetalleOut,
    TarifarioIn,
    TarifarioOpcionesOut,
    TarifarioOut,
    TarifariosFilters,
)
from transportista.use_cases import (
    ActualizarTarifarioUseCase,
    CerrarTarifarioUseCase,
    CrearTarifarioUseCase,
    EliminarTarifarioUseCase,
    ListarTarifariosUseCase,
    ObtenerTarifarioUseCase,
    OpcionesTarifarioUseCase,
)

tarifarios_router = Router(tags=["tarifarios"])


@tarifarios_router.get(
    "/opciones",
    response={200: TarifarioOpcionesOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_VER),
    summary="Todo lo que el formulario de tarifario necesita para poblar sus selects",
    operation_id="opcionesTarifario",
)
def opciones_tarifario(request: HttpRequest):
    return 200, OpcionesTarifarioUseCase.execute()


@tarifarios_router.get(
    "/",
    response={200: list[TarifarioOut], **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_VER),
    summary="Lista los tarifarios activos con la cantidad de tarifas de cada uno",
    operation_id="listarTarifarios",
)
def listar_tarifarios(request: HttpRequest, filters: Query[TarifariosFilters]):
    return 200, ListarTarifariosUseCase.execute(filters)


@tarifarios_router.post(
    "/",
    response={201: TarifarioDetalleOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_CREAR),
    summary="Crea un tarifario con sus tarifas de flete y de concepto adicional",
    operation_id="crearTarifario",
)
def crear_tarifario(request: HttpRequest, payload: TarifarioIn):
    return 201, CrearTarifarioUseCase.execute(payload)


@tarifarios_router.get(
    "/{int:tarifario_id}",
    response={200: TarifarioDetalleOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_VER),
    summary="Obtiene un tarifario con sus dos colecciones de tarifas",
    operation_id="obtenerTarifario",
)
def obtener_tarifario(request: HttpRequest, tarifario_id: int):
    return 200, ObtenerTarifarioUseCase.execute(tarifario_id)


@tarifarios_router.put(
    "/{int:tarifario_id}",
    response={200: TarifarioDetalleOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_EDITAR),
    summary="Reemplaza un tarifario y sus tarifas",
    description=(
        "Un tarifario ya usado para costear una orden de servicio responde 409: la salida es "
        "cerrar su vigencia y crear uno nuevo."
    ),
    operation_id="actualizarTarifario",
)
def actualizar_tarifario(request: HttpRequest, tarifario_id: int, payload: TarifarioIn):
    return 200, ActualizarTarifarioUseCase.execute(tarifario_id, payload)


@tarifarios_router.post(
    "/{int:tarifario_id}/cerrar",
    response={200: TarifarioOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_EDITAR),
    summary="Cierra la vigencia de un tarifario",
    operation_id="cerrarTarifario",
)
def cerrar_tarifario(request: HttpRequest, tarifario_id: int, payload: CerrarTarifarioIn):
    return 200, CerrarTarifarioUseCase.execute(tarifario_id, payload)


@tarifarios_router.delete(
    "/{int:tarifario_id}",
    response={204: None, **ERRORS},
    auth=SessionAuth(PermisoCodigo.TARIFARIOS_ELIMINAR),
    summary="Da de baja lógica un tarifario y sus tarifas",
    operation_id="eliminarTarifario",
)
def eliminar_tarifario(request: HttpRequest, tarifario_id: int):
    EliminarTarifarioUseCase.execute(tarifario_id)
    return 204, None
