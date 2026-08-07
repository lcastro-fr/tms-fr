from __future__ import annotations

from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Prefetch

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

    @staticmethod
    def list_by_orden_servicio(orden_servicio_id: int) -> list[tuple[Remito, list[RemitoDestino]]]:
        """
        Los remitos de una OS con sus destinos ya resueltos, en dos queries.
        """
        remitos = (
            Remito.objects.filter(orden_servicio_id=orden_servicio_id)
            .prefetch_related(
                Prefetch(
                    "destinos",
                    queryset=RemitoDestino.objects.filter(active=True)
                    .select_related("ubicacion", "ubicacion__pais")
                    .order_by("id"),
                )
            )
            .order_by("numero")
        )
        return [(remito, list(remito.destinos.all())) for remito in remitos]

    @staticmethod
    def get_distinct_destinos(orden_servicio_id: int) -> list[Ubicacion]:
        return list(
            Ubicacion.objects.filter(
                remitos_destino__active=True,
                remitos_destino__remito__active=True,
                remitos_destino__remito__orden_servicio_id=orden_servicio_id,
            )
            .distinct()
            .order_by("id")
        )
