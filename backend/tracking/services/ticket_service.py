from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings

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

    class TicketSinEgresoError(BusinessRuleError):
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
    def get_dias_permanencia(orden_servicio_id: int) -> int:
        """
        Días cobrables de permanencia de los tickets de una orden de servicio. La estadia empieza cuando cambia el dia.
        """
        tz = ZoneInfo(settings.TZ_OPERACION)
        tickets = Ticket.objects.filter(orden_servicio_id=orden_servicio_id)

        dias = 0
        for ticket in tickets:
            if ticket.fecha_egreso is None:
                raise TicketService.TicketSinEgresoError(
                    f"El ticket {ticket.numero} no tiene fecha_egreso, no se puede costear",
                    detail={"ticket": ticket.numero},
                )
            ingreso = ticket.fecha_ingreso.astimezone(tz).date()
            egreso = ticket.fecha_egreso.astimezone(tz).date()
            dias += (egreso - ingreso).days
        return dias

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
