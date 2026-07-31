from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, Field

from catalog.dtos import CodigoUbicacion
from transportista.dtos import TransportistaIn

if TYPE_CHECKING:
    from tracking.models import Ticket


class TicketIngestRemitoIn(BaseModel):
    numero: str = Field(min_length=1, max_length=13)
    fecha: AwareDatetime | None = None
    destinos: list[CodigoUbicacion] = Field(min_length=1)


class TicketIngestIn(BaseModel):
    numero: str = Field(min_length=1, max_length=20)
    planta_codigo: CodigoUbicacion
    fecha_ingreso: AwareDatetime
    fecha_egreso: AwareDatetime | None = None
    transportista: TransportistaIn
    remitos: list[TicketIngestRemitoIn] = Field(default_factory=list)


class RemitoOmitidoOut(BaseModel):
    numero: str
    motivo: str


class TicketIngestOut(BaseModel):
    ticket_id: int
    numero: str
    orden_servicio_id: int
    remitos_creados: list[str]
    remitos_omitidos: list[RemitoOmitidoOut]

    @property
    def completo(self) -> bool:
        return not self.remitos_omitidos

    @classmethod
    def from_model(
        cls,
        ticket: Ticket,
        remitos_creados: list[str],
        remitos_omitidos: list[RemitoOmitidoOut],
    ) -> TicketIngestOut:
        return cls(
            ticket_id=ticket.id,
            numero=ticket.numero,
            orden_servicio_id=ticket.orden_servicio_id,
            remitos_creados=remitos_creados,
            remitos_omitidos=remitos_omitidos,
        )
