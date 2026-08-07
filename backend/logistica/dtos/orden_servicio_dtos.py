from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Self

from pydantic import AwareDatetime, BaseModel

from catalog.enums import TipoCamion
from logistica.dtos.costo_dtos import CostoOrdenServicioOut
from transportista.enums import TipoOperacion, Via

if TYPE_CHECKING:
    from logistica.models import CostoOrdenServicio, OrdenServicio
    from tracking.models import Remito, RemitoDestino, Ticket


class OpcionOut(BaseModel):
    value: str
    label: str


class OrdenServicioOpcionesOut(BaseModel):
    tipos_operacion: list[OpcionOut]
    tipos_camion: list[OpcionOut]
    vias: list[OpcionOut]

    @classmethod
    def from_choices(
        cls,
        tipos_operacion: list[tuple[str, str]],
        tipos_camion: list[tuple[str, str]],
        vias: list[tuple[str, str]],
    ) -> OrdenServicioOpcionesOut:
        def opciones(choices: list[tuple[str, str]]) -> list[OpcionOut]:
            return [OpcionOut(value=value, label=label) for value, label in choices]

        return cls(
            tipos_operacion=opciones(tipos_operacion),
            tipos_camion=opciones(tipos_camion),
            vias=opciones(vias),
        )


class OrdenServicioIn(BaseModel):
    fecha_viaje: AwareDatetime | None = None
    tipo_operacion: TipoOperacion
    tipo_camion: TipoCamion | None = None
    via: Via
    hombreador: bool = False
    facturable: bool = False


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
    hombreador: bool
    facturable: bool
    active: bool
    costo: CostoOrdenServicioOut | None = None
    tickets: list[TicketOut] = []

    # Devuelve Self y acepta **extra para que la subclase de detalle reuse este mapeo.
    @classmethod
    def from_model(
        cls,
        orden: OrdenServicio,
        costo: CostoOrdenServicio | None = None,
        tickets: list[TicketOut] | None = None,
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
            hombreador=orden.hombreador,
            facturable=orden.facturable,
            active=orden.active,
            costo=CostoOrdenServicioOut.from_model(costo) if costo else None,
            tickets=tickets or [],
            **extra,
        )


class OrdenServicioDetalleOut(OrdenServicioOut):
    """
    La OS con todo lo que cuelga de ella. Los remitos no van en la lista: son N por OS,
    con M destinos cada uno.
    """

    remitos: list[RemitoOut] = []

    @classmethod
    def from_model(
        cls,
        orden: OrdenServicio,
        costo: CostoOrdenServicio | None = None,
        tickets: list[TicketOut] | None = None,
        remitos: list[tuple[Remito, list[RemitoDestino]]] | None = None,
        **extra,
    ) -> Self:
        return super().from_model(
            orden,
            costo,
            tickets,
            remitos=[RemitoOut.from_model(r, destinos) for r, destinos in remitos or []],
            **extra,
        )
