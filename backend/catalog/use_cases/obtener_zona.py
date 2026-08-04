from __future__ import annotations

from catalog.dtos import ZonaOut
from catalog.services import ZonaService


class ObtenerZonaUseCase:
    @staticmethod
    def execute(zona_id: int) -> ZonaOut:
        return ZonaOut.from_model(ZonaService.get_zona_or_raise(zona_id))
