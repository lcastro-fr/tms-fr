from __future__ import annotations

from catalog.dtos import ZonaOut
from catalog.services import ZonaService


class ListarZonasUseCase:
    @staticmethod
    def execute() -> list[ZonaOut]:
        return [ZonaOut.from_model(zona) for zona in ZonaService.list_zonas()]
