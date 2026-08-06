from __future__ import annotations

from catalog.dtos import UbicacionIn, UbicacionOut
from catalog.services import UbicacionService


class ActualizarUbicacionUseCase:
    @staticmethod
    def execute(ubicacion_id: int, data: UbicacionIn) -> UbicacionOut:
        ubicacion = UbicacionService.get_ubicacion_or_raise(ubicacion_id)
        lng, lat = data.coordinates.coordinates
        ubicacion = UbicacionService.update_ubicacion(
            ubicacion, nombre=data.nombre, tipo=data.tipo.value, lat=lat, lng=lng
        )
        return UbicacionOut.from_model(ubicacion)
