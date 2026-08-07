from __future__ import annotations

from catalog.dtos import ZonaIn, ZonaOut
from catalog.services import ZonaService


class ActualizarZonaUseCase:
    @staticmethod
    def execute(zona_id: int, data: ZonaIn) -> ZonaOut:
        zona = ZonaService.get_zona_or_raise(zona_id)
        zona = ZonaService.update_zona(zona, nombre=data.nombre, coordinates=data.geom.coordinates)
        return ZonaOut.from_model(zona)
