from __future__ import annotations

from catalog.dtos import ZonaIn, ZonaOut
from catalog.services import ZonaService


class CrearZonaUseCase:
    @staticmethod
    def execute(data: ZonaIn) -> ZonaOut:
        zona = ZonaService.create_zona(nombre=data.nombre, coordinates=data.geom.coordinates)
        return ZonaOut.from_model(zona)
