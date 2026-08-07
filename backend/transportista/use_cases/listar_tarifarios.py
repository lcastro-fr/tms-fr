from __future__ import annotations

from transportista.dtos import TarifarioOut, TarifariosFilters
from transportista.services import TarifarioService


class ListarTarifariosUseCase:
    @staticmethod
    def execute(filters: TarifariosFilters) -> list[TarifarioOut]:
        tarifarios = TarifarioService.list_tarifarios(
            transportista_id=filters.transportista_id, vencidos=filters.vencidos
        )
        ids = [t.id for t in tarifarios]
        en_uso = TarifarioService.tarifarios_en_uso(ids)
        conteos = TarifarioService.contar_tarifas(ids)
        return [
            TarifarioOut.from_model(
                tarifario,
                en_uso=tarifario.id in en_uso,
                cantidad_fletes=conteos[tarifario.id][0],
                cantidad_conceptos=conteos[tarifario.id][1],
            )
            for tarifario in tarifarios
        ]
