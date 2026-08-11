from __future__ import annotations

from catalog.enums import TIPO_CAMION_CHOICES
from catalog.services import UbicacionService
from logistica.dtos import OrdenServicioOpcionesOut
from transportista.enums import TIPO_OPERACION_CHOICES, VIA_CHOICES


class OpcionesOrdenServicioUseCase:
    @staticmethod
    def execute() -> OrdenServicioOpcionesOut:
        return OrdenServicioOpcionesOut.from_choices(
            tipos_operacion=TIPO_OPERACION_CHOICES,
            tipos_camion=TIPO_CAMION_CHOICES,
            vias=VIA_CHOICES,
            ubicaciones=UbicacionService.list_ubicaciones_para_opciones(),
        )
