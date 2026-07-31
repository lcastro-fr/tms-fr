from __future__ import annotations

from datetime import datetime

from catalog.enums import TipoUbicacion
from catalog.models import Ubicacion
from logistica.models import OrdenServicio
from shared.exceptions import BusinessRuleError, ConflictError
from tracking.models import Ticket


class TicketService:
    class InvalidUbicacionError(BusinessRuleError):
        pass

    class TicketAlreadyExistsError(ConflictError):
        pass

    @staticmethod
    def _check_uq_ticket(ubicacion: Ubicacion, numero: str) -> None:
        if Ticket.objects.filter(numero=numero, planta=ubicacion).exists():
            raise TicketService.TicketAlreadyExistsError(
                f"Ticket con número {numero} ya existe en la ubicación {ubicacion}",
                detail={"numero": numero, "planta": str(ubicacion)},
            )

    @staticmethod
    def _check_valid_ubicacion(ubicacion: Ubicacion) -> None:
        if ubicacion.tipo != TipoUbicacion.PLANTA:
            raise TicketService.InvalidUbicacionError(
                f"Ubicación {ubicacion} no es de tipo PLANTA",
                detail={"ubicacion": str(ubicacion), "tipo": ubicacion.tipo},
            )

    @staticmethod
    def create_ticket(
        planta: Ubicacion,
        numero: str,
        orden_servicio: OrdenServicio,
        fecha_ingreso: datetime,
        fecha_egreso: datetime | None,
    ) -> Ticket:
        TicketService._check_valid_ubicacion(planta)
        TicketService._check_uq_ticket(planta, numero)

        return Ticket.objects.create(
            planta=planta,
            numero=numero,
            orden_servicio=orden_servicio,
            fecha_ingreso=fecha_ingreso,
            fecha_egreso=fecha_egreso,
        )
