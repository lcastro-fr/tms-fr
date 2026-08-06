from __future__ import annotations

from catalog.dtos import UbicacionesFilters, UbicacionOut
from catalog.services import UbicacionService


class ListarUbicacionesUseCase:
    @staticmethod
    def execute(filters: UbicacionesFilters) -> list[UbicacionOut]:
        ubicaciones = UbicacionService.list_ubicaciones(
            validada=filters.validada, con_coordenadas=filters.con_coordenadas
        )
        return [UbicacionOut.from_model(ubicacion) for ubicacion in ubicaciones]
