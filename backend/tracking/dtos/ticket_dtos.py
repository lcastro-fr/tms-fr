from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, Field, computed_field

from catalog.dtos import CodigoUbicacion
from transportista.dtos import TransportistaIn
from enum import StrEnum

if TYPE_CHECKING:
    from tracking.models import Ticket

class TipoTransporte(StrEnum):
    PROPIO = "PROPIO"
    CONTRATADO = "CONTRATADO"

class RemitoUbicacionIn(BaseModel):
    codigo: str
    nombre: str
    pais: str
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None


class TicketIngestRemitoIn(BaseModel):
    numero: str = Field(min_length=1, max_length=13)
    fecha: AwareDatetime | None = None
    destinos: list[RemitoUbicacionIn] = Field(min_length=1)


class TicketIngestIn(BaseModel):
    numero: str = Field(min_length=1, max_length=20)
    planta_codigo: CodigoUbicacion
    fecha_ingreso: AwareDatetime
    fecha_egreso: AwareDatetime | None = None
    transportista: TransportistaIn
    remitos: list[TicketIngestRemitoIn] = Field(default_factory=list)
    tipo_transp: TipoTransporte | None = None

    @computed_field
    @property
    def facturable(self) -> bool:
        return self.tipo_transp == TipoTransporte.CONTRATADO


class RemitoOmitidoOut(BaseModel):
    numero: str
    motivo: str


class DestinoSinGeolocalizarOut(BaseModel):
    codigo: str
    nombre: str
    motivo: str


class DestinoSinPaisOut(BaseModel):
    codigo: str
    nombre: str
    pais_recibido: str


class TicketIngestOut(BaseModel):
    ticket_id: int
    numero: str
    orden_servicio_id: int
    remitos_creados: list[str]
    remitos_omitidos: list[RemitoOmitidoOut]
    destinos_sin_geolocalizar: list[DestinoSinGeolocalizarOut]
    destinos_sin_pais: list[DestinoSinPaisOut]

    @property
    def completo(self) -> bool:
        return not (
            self.remitos_omitidos or self.destinos_sin_geolocalizar or self.destinos_sin_pais
        )

    @classmethod
    def from_model(
        cls,
        ticket: Ticket,
        remitos_creados: list[str],
        remitos_omitidos: list[RemitoOmitidoOut],
        destinos_sin_geolocalizar: list[DestinoSinGeolocalizarOut],
        destinos_sin_pais: list[DestinoSinPaisOut],
    ) -> TicketIngestOut:
        return cls(
            ticket_id=ticket.id,
            numero=ticket.numero,
            orden_servicio_id=ticket.orden_servicio_id,
            remitos_creados=remitos_creados,
            remitos_omitidos=remitos_omitidos,
            destinos_sin_geolocalizar=destinos_sin_geolocalizar,
            destinos_sin_pais=destinos_sin_pais,
        )
