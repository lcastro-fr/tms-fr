from __future__ import annotations

from django.db import transaction

from transportista.dtos import TarifarioDetalleOut, TarifarioIn
from transportista.services import TarifarioService


class ActualizarTarifarioUseCase:
    """
    Un tarifario que ya se usó para costear no se edita.

    """

    @staticmethod
    @transaction.atomic
    def execute(tarifario_id: int, data: TarifarioIn) -> TarifarioDetalleOut:
        tarifario = TarifarioService.get_tarifario_or_raise(tarifario_id)
        if TarifarioService.esta_en_uso(tarifario.id):
            raise TarifarioService.TarifarioEnUsoError(
                "El tarifario ya se usó para costear una orden de servicio: cerrá su vigencia "
                "y cargá uno nuevo",
                detail={"tarifario_id": tarifario.id, "motivo": "en_uso"},
            )

        tarifario = TarifarioService.update_tarifario(
            tarifario,
            transportista_id=data.transportista_id,
            vigente_desde=data.vigente_desde,
            vigente_hasta=data.vigente_hasta,
        )
        TarifarioService.replace_hijos(
            tarifario,
            fletes=[f.model_dump() for f in data.tarifas_flete],
            conceptos=[c.model_dump() for c in data.tarifas_concepto],
        )
        fletes, conceptos = TarifarioService.get_hijos(tarifario.id)
        return TarifarioDetalleOut.from_model(tarifario, fletes=fletes, conceptos=conceptos)
