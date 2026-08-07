from __future__ import annotations

from transportista.dtos import TarifarioDetalleOut
from transportista.services import TarifarioService


class ObtenerTarifarioUseCase:
    @staticmethod
    def execute(tarifario_id: int) -> TarifarioDetalleOut:
        tarifario = TarifarioService.get_tarifario_or_raise(tarifario_id)
        fletes, conceptos = TarifarioService.get_hijos(tarifario.id)
        return TarifarioDetalleOut.from_model(
            tarifario,
            en_uso=TarifarioService.esta_en_uso(tarifario.id),
            fletes=fletes,
            conceptos=conceptos,
        )
