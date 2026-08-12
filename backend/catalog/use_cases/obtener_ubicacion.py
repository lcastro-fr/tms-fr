from __future__ import annotations

from catalog.dtos import UbicacionOut
from catalog.services import UbicacionService


class ObtenerUbicacionUseCase:
    @staticmethod
    def execute(ubicacion_id: int) -> UbicacionOut:
        return UbicacionOut.from_model(UbicacionService.get_ubicacion_or_raise(ubicacion_id))
