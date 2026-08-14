from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import AwareDatetime, BaseModel, Field

from catalog.dtos import UbicacionOpcionOut
from catalog.enums import TipoCamion
from logistica.dtos.costo_dtos import CostoOrdenServicioOut
from shared.dtos import OpcionOut
from transportista.enums import ModalidadFlete, TipoOperacion, Via

if TYPE_CHECKING:
    from catalog.models import Ubicacion
    from logistica.models import CostoOrdenServicio, OrdenServicio
    from tracking.models import Remito, RemitoDestino, Ticket


class OrdenServicioOpcionesOut(BaseModel):
    tipos_operacion: list[OpcionOut]
    tipos_camion: list[OpcionOut]
    vias: list[OpcionOut]
    modalidades: list[OpcionOut]
    ubicaciones: list[UbicacionOpcionOut]

    @classmethod
    def from_choices(
        cls,
        tipos_operacion: list[tuple[str, str]],
        tipos_camion: list[tuple[str, str]],
        vias: list[tuple[str, str]],
        modalidades: list[tuple[str, str]],
        ubicaciones: list[Ubicacion],
    ) -> OrdenServicioOpcionesOut:
        return cls(
            tipos_operacion=OpcionOut.desde_choices(tipos_operacion),
            tipos_camion=OpcionOut.desde_choices(tipos_camion),
            vias=OpcionOut.desde_choices(vias),
            modalidades=OpcionOut.desde_choices(modalidades),
            ubicaciones=[UbicacionOpcionOut.from_model(u) for u in ubicaciones],
        )


class OrdenServicioDestinoIn(BaseModel):
    ubicacion_id: int


CostoReal = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class OrdenServicioIn(BaseModel):
    fecha_viaje: AwareDatetime | None = None
    tipo_operacion: TipoOperacion
    tipo_camion: TipoCamion | None = None
    via: Via
    modalidad: ModalidadFlete | None = None
    hombreador: bool = False
    facturable: bool = False
    costo_real: CostoReal | None = None
    observaciones: str = Field("", max_length=2000)
    destinos: list[OrdenServicioDestinoIn] | None = None


class OrdenesServicioFilters(BaseModel):
    facturable: bool | None = None
    con_costo: bool | None = None
    numero: str | None = None
    fecha_viaje_desde: date | None = None
    fecha_viaje_hasta: date | None = None
    incluir_sin_fecha: bool | None = None


class TicketOut(BaseModel):
    id: int
    numero: str
    planta_codigo: str | None
    planta_nombre: str
    fecha_ingreso: AwareDatetime
    fecha_egreso: AwareDatetime | None
    dias_estadia: int | None

    @classmethod
    def from_model(cls, ticket: Ticket, dias_estadia: int | None) -> TicketOut:
        return cls(
            id=ticket.id,
            numero=ticket.numero,
            planta_codigo=ticket.planta.codigo,
            planta_nombre=ticket.planta.nombre,
            fecha_ingreso=ticket.fecha_ingreso,
            fecha_egreso=ticket.fecha_egreso,
            dias_estadia=dias_estadia,
        )


class RemitoDestinoOut(BaseModel):
    ubicacion_id: int
    codigo: str | None
    nombre: str
    pais: str | None

    @classmethod
    def from_model(cls, destino: RemitoDestino) -> RemitoDestinoOut:
        ubicacion = destino.ubicacion
        return cls(
            ubicacion_id=ubicacion.id,
            codigo=ubicacion.codigo,
            nombre=ubicacion.nombre,
            pais=ubicacion.pais.nombre if ubicacion.pais else None,
        )


class OrdenServicioDestinoOut(BaseModel):
    """Sirve para los destinos explícitos y para los sugeridos por los remitos."""

    ubicacion_id: int
    codigo: str | None
    nombre: str
    tipo: str
    pais: str | None
    tiene_coordenadas: bool
    secuencia: int

    @classmethod
    def from_ubicacion(cls, ubicacion: Ubicacion, secuencia: int) -> OrdenServicioDestinoOut:
        return cls(
            ubicacion_id=ubicacion.id,
            codigo=ubicacion.codigo,
            nombre=ubicacion.nombre,
            tipo=ubicacion.tipo,
            pais=ubicacion.pais.nombre if ubicacion.pais else None,
            tiene_coordenadas=ubicacion.coordinates is not None,
            secuencia=secuencia,
        )


class RemitoOut(BaseModel):
    id: int
    numero: str
    fecha: AwareDatetime | None
    destinos: list[RemitoDestinoOut]

    @classmethod
    def from_model(cls, remito: Remito, destinos: list[RemitoDestino]) -> RemitoOut:
        return cls(
            id=remito.id,
            numero=remito.numero,
            fecha=remito.fecha,
            destinos=[RemitoDestinoOut.from_model(d) for d in destinos],
        )


class OrdenServicioOut(BaseModel):
    id: int
    origen_id: int
    origen_codigo: str | None
    origen_nombre: str
    transportista_id: int
    transportista_razon_social: str
    fecha_viaje: AwareDatetime | None
    tipo_operacion: str
    tipo_camion: str | None
    via: str
    modalidad: str | None
    hombreador: bool
    facturable: bool
    costo_real: Decimal | None
    observaciones: str
    active: bool
    costo: CostoOrdenServicioOut | None = None
    tickets: list[TicketOut] = []
    costo_desactualizado: bool = False

    # Devuelve Self y acepta **extra para que la subclase de detalle reuse este mapeo.
    @classmethod
    def from_model(
        cls,
        orden: OrdenServicio,
        costo: CostoOrdenServicio | None = None,
        tickets: list[TicketOut] | None = None,
        costo_desactualizado: bool = False,
        **extra,
    ) -> Self:
        return cls(
            id=orden.id,
            origen_id=orden.origen_id,
            origen_codigo=orden.origen.codigo,
            origen_nombre=orden.origen.nombre,
            transportista_id=orden.transportista_id,
            transportista_razon_social=orden.transportista.razon_social,
            fecha_viaje=orden.fecha_viaje,
            tipo_operacion=orden.tipo_operacion,
            tipo_camion=orden.tipo_camion,
            via=orden.via,
            modalidad=orden.modalidad,
            hombreador=orden.hombreador,
            facturable=orden.facturable,
            costo_real=orden.costo_real,
            observaciones=orden.observaciones,
            active=orden.active,
            costo=CostoOrdenServicioOut.from_model(costo) if costo else None,
            tickets=tickets or [],
            costo_desactualizado=costo_desactualizado,
            **extra,
        )


class OrdenServicioDetalleOut(OrdenServicioOut):
    """
    La OS con todo lo que cuelga de ella. Los remitos no van en la lista: son N por OS,
    con M destinos cada uno.
    """

    remitos: list[RemitoOut] = []
    destinos: list[OrdenServicioDestinoOut] = []
    destinos_sugeridos: list[OrdenServicioDestinoOut] = []
    origen_destinos: str

    @classmethod
    def from_model(
        cls,
        orden: OrdenServicio,
        costo: CostoOrdenServicio | None = None,
        tickets: list[TicketOut] | None = None,
        costo_desactualizado: bool = False,
        remitos: list[tuple[Remito, list[RemitoDestino]]] | None = None,
        destinos: list[Ubicacion] | None = None,
        destinos_sugeridos: list[Ubicacion] | None = None,
        origen_destinos: str = "",
        **extra,
    ) -> Self:
        return super().from_model(
            orden,
            costo,
            tickets,
            costo_desactualizado,
            remitos=[RemitoOut.from_model(r, destinos_) for r, destinos_ in remitos or []],
            destinos=[
                OrdenServicioDestinoOut.from_ubicacion(u, i) for i, u in enumerate(destinos or [])
            ],
            destinos_sugeridos=[
                OrdenServicioDestinoOut.from_ubicacion(u, i)
                for i, u in enumerate(destinos_sugeridos or [])
            ],
            origen_destinos=origen_destinos,
            **extra,
        )
