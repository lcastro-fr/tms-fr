from __future__ import annotations

from catalog.services import ZonaService


class EliminarZonaUseCase:
    @staticmethod
    def execute(zona_id: int) -> None:
        zona = ZonaService.get_zona_or_raise(zona_id)
        ZonaService.delete_zona(zona)
