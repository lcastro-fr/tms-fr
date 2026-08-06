from __future__ import annotations

from catalog.dtos import UbicacionOut
from catalog.services import UbicacionService


class ListarUbicacionesUseCase:
    @staticmethod
    def execute() -> list[UbicacionOut]:
        return [
            UbicacionOut.from_model(ubicacion)
            for ubicacion in UbicacionService.list_ubicaciones()
        ]
