from __future__ import annotations

from catalog.dtos import UbicacionOpcionesOut
from catalog.enums import TIPO_UBICACION_CHOICES
from catalog.services import PaisService


class OpcionesUbicacionUseCase:
    """
    Los tipos salen del enum, así que agregar un valor lo publica solo.
    """

    @staticmethod
    def execute() -> UbicacionOpcionesOut:
        return UbicacionOpcionesOut.from_choices(
            tipos_ubicacion=TIPO_UBICACION_CHOICES,
            paises=PaisService.list_paises(),
        )
