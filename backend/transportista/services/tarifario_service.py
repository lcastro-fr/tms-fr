from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Q

from shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from transportista.models import Tarifario, Transportista


class TarifarioService:
    class TransportistaNotFoundError(NotFoundError):
        pass

    class VigenciaInvalidaError(BusinessRuleError):
        pass

    class TarifarioSolapadoError(ConflictError):
        pass


    @staticmethod
    def _check_vigencia(vigente_desde: date, vigente_hasta: date | None) -> None:
        if vigente_hasta is not None and vigente_hasta < vigente_desde:
            raise TarifarioService.VigenciaInvalidaError(
                f"vigente_hasta ({vigente_hasta}) es anterior a vigente_desde ({vigente_desde})",
                detail={
                    "vigente_desde": str(vigente_desde),
                    "vigente_hasta": str(vigente_hasta),
                },
            )

    @staticmethod
    def _check_solapamiento(
        transportista_id: int,
        vigente_desde: date,
        vigente_hasta: date | None,
        excluir_id: int | None = None,
    ) -> None:
        qs = Tarifario.objects.filter(transportista_id=transportista_id).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=vigente_desde)
        )
        if vigente_hasta is not None:
            qs = qs.filter(vigente_desde__lte=vigente_hasta)
        if excluir_id is not None:
            qs = qs.exclude(pk=excluir_id)

        conflicto = qs.first()
        if conflicto is not None:
            raise TarifarioService.TarifarioSolapadoError(
                f"La vigencia se solapa con el tarifario {conflicto.id} "
                f"({conflicto.vigente_desde} - {conflicto.vigente_hasta or 'sin cierre'})",
                detail={
                    "tarifario_id": conflicto.id,
                    "vigente_desde": str(conflicto.vigente_desde),
                    "vigente_hasta": (
                        str(conflicto.vigente_hasta) if conflicto.vigente_hasta else None
                    ),
                },
            )

    @staticmethod
    def _lock_transportista(transportista_id: int) -> None:
        existe = Transportista.all_objects.select_for_update().filter(pk=transportista_id).exists()
        if not existe:
            raise TarifarioService.TransportistaNotFoundError(
                f"No existe el transportista {transportista_id}",
                detail={"transportista_id": transportista_id},
            )

    @staticmethod
    def create_tarifario(
        transportista_id: int,
        vigente_desde: date,
        vigente_hasta: date | None = None,
    ) -> Tarifario:
        TarifarioService._check_vigencia(vigente_desde, vigente_hasta)

        with transaction.atomic():
            TarifarioService._lock_transportista(transportista_id)
            TarifarioService._check_solapamiento(transportista_id, vigente_desde, vigente_hasta)
            return Tarifario.objects.create(
                transportista_id=transportista_id,
                vigente_desde=vigente_desde,
                vigente_hasta=vigente_hasta,
            )

    @staticmethod
    def cerrar_tarifario(tarifario: Tarifario, vigente_hasta: date) -> Tarifario:
        TarifarioService._check_vigencia(tarifario.vigente_desde, vigente_hasta)

        with transaction.atomic():
            TarifarioService._lock_transportista(tarifario.transportista_id)
            TarifarioService._check_solapamiento(
                tarifario.transportista_id,
                tarifario.vigente_desde,
                vigente_hasta,
                excluir_id=tarifario.id,
            )
            tarifario.vigente_hasta = vigente_hasta
            tarifario.save(update_fields=["vigente_hasta", "updated_at"])
            return tarifario
