from __future__ import annotations

from transportista.dtos import CerrarTarifarioIn, TarifarioOut
from transportista.services import TarifarioService


class CerrarTarifarioUseCase:
    """Cerrar la vigencia se permite aunque el tarifario esté en uso: es la salida del PUT."""

    @staticmethod
    def execute(tarifario_id: int, data: CerrarTarifarioIn) -> TarifarioOut:
        tarifario = TarifarioService.get_tarifario_or_raise(tarifario_id)
        tarifario = TarifarioService.cerrar_tarifario(tarifario, data.vigente_hasta)
        fletes, conceptos = TarifarioService.get_hijos(tarifario.id)
        return TarifarioOut.from_model(
            tarifario,
            en_uso=TarifarioService.esta_en_uso(tarifario.id),
            cantidad_fletes=len(fletes),
            cantidad_conceptos=len(conceptos),
        )
