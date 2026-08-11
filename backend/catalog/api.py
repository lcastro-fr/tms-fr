from __future__ import annotations

from django.http import HttpRequest
from ninja import Query, Router

from catalog.dtos import (
    GeocodificarUbicacionIn,
    UbicacionCrearIn,
    UbicacionesFilters,
    UbicacionGeocodificadaOut,
    UbicacionIn,
    UbicacionOpcionesOut,
    UbicacionOut,
    ZonaIn,
    ZonaOut,
)
from catalog.use_cases import (
    ActualizarUbicacionUseCase,
    ActualizarZonaUseCase,
    CrearUbicacionUseCase,
    CrearZonaUseCase,
    EliminarZonaUseCase,
    GeocodificarUbicacionUseCase,
    ListarUbicacionesUseCase,
    ListarZonasUseCase,
    ObtenerZonaUseCase,
    OpcionesUbicacionUseCase,
)
from core.auth import SessionAuth
from routing.factory import build_geocoder
from shared.dtos import ERRORS
from shared.permisos import PermisoCodigo

zonas_router = Router(tags=["zonas"])
ubicaciones_router = Router(tags=["ubicaciones"])


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


@zonas_router.delete(
    "/{int:zona_id}",
    response={204: None, **ERRORS},
    auth=SessionAuth(PermisoCodigo.ZONAS_ELIMINAR),
    summary="Da de baja lógica una zona",
    operation_id="eliminarZona",
)
def eliminar_zona(request: HttpRequest, zona_id: int):
    EliminarZonaUseCase.execute(zona_id)
    return 204, None


@ubicaciones_router.get(
    "/",
    response={200: list[UbicacionOut], **ERRORS},
    auth=SessionAuth(PermisoCodigo.UBICACIONES_VER),
    summary="Lista las ubicaciones activas",
    operation_id="listarUbicaciones",
)
def listar_ubicaciones(request: HttpRequest, filters: Query[UbicacionesFilters]):
    return 200, ListarUbicacionesUseCase.execute(filters)


@ubicaciones_router.get(
    "/opciones",
    response={200: UbicacionOpcionesOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.UBICACIONES_VER),
    summary="Tipos de ubicación y países para el formulario",
    operation_id="opcionesUbicacion",
)
def opciones_ubicacion(request: HttpRequest):
    return 200, OpcionesUbicacionUseCase.execute()


@ubicaciones_router.post(
    "/geocodificar",
    response={200: UbicacionGeocodificadaOut, **ERRORS},
    # SessionAuth es OR: alcanza con crear o con editar.
    auth=SessionAuth(PermisoCodigo.UBICACIONES_CREAR, PermisoCodigo.UBICACIONES_EDITAR),
    summary="Busca la coordenada de una dirección sin guardar nada",
    description=(
        "Es un preview: no crea ni modifica nada. Sólo geolocaliza direcciones de los países "
        "que soporta el proveedor; para el resto hay que marcar el punto a mano."
    ),
    operation_id="geocodificarUbicacion",
)
def geocodificar_ubicacion(request: HttpRequest, payload: GeocodificarUbicacionIn):
    return 200, GeocodificarUbicacionUseCase(build_geocoder()).execute(payload)


@ubicaciones_router.post(
    "/",
    response={201: UbicacionOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.UBICACIONES_CREAR),
    summary="Crea una ubicación validada",
    description=(
        "La coordenada es obligatoria y la ubicación nace validada. El código es opcional: "
        "es la clave con la que la ingesta de SAP reconoce sus filas, así que si se le pone "
        "uno que SAP también use, la próxima ingesta gana sobre el nombre y la dirección."
    ),
    operation_id="crearUbicacion",
)
def crear_ubicacion(request: HttpRequest, payload: UbicacionCrearIn):
    return 201, CrearUbicacionUseCase.execute(payload)


@ubicaciones_router.put(
    "/{int:ubicacion_id}",
    response={200: UbicacionOut, **ERRORS},
    auth=SessionAuth(PermisoCodigo.UBICACIONES_EDITAR),
    summary="Corrige una ubicación y la marca como validada",
    operation_id="actualizarUbicacion",
)
def actualizar_ubicacion(request: HttpRequest, ubicacion_id: int, payload: UbicacionIn):
    return 200, ActualizarUbicacionUseCase.execute(ubicacion_id, payload)
