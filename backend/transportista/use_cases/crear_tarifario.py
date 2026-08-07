from __future__ import annotations

from django.db import transaction

from transportista.dtos import TarifarioDetalleOut, TarifarioIn
from transportista.services import TarifarioService


class CrearTarifarioUseCase:
    @staticmethod
    @transaction.atomic
    def execute(data: TarifarioIn) -> TarifarioDetalleOut:
        tarifario = TarifarioService.create_tarifario(
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
