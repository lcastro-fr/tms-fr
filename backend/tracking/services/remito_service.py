from __future__ import annotations

from datetime import datetime

from django.db import IntegrityError, transaction

from catalog.models import Ubicacion
from logistica.models import OrdenServicio
from shared.exceptions import ConflictError
from tracking.models import Remito, RemitoDestino


class RemitoService:
    class RemitoAlreadyExistsError(ConflictError):
        pass

    @staticmethod
    def create_remito(
        numero: str,
        fecha: datetime | None,
        orden_servicio: OrdenServicio,
        destinos: list[Ubicacion],
    ) -> Remito:
        destinos_unicos = list(dict.fromkeys(destinos))

        try:
            with transaction.atomic():
                remito = Remito.objects.create(
                    numero=numero,
                    fecha=fecha,
                    orden_servicio=orden_servicio,
                )
                RemitoDestino.objects.bulk_create(
                    [RemitoDestino(remito=remito, ubicacion=u) for u in destinos_unicos]
                )
        except IntegrityError as exc:
            raise RemitoService.RemitoAlreadyExistsError(
                f"Remito con número {numero} ya existe.",
                detail={"numero": numero},
            ) from exc

        return remito

    @staticmethod
    def add_destino(remito: Remito, ubicacion: Ubicacion) -> RemitoDestino:
        return RemitoDestino.objects.create(remito=remito, ubicacion=ubicacion)
