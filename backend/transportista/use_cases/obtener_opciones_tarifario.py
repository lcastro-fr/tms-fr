from __future__ import annotations

from catalog.enums import TIPO_CAMION_CHOICES
from catalog.services import UbicacionService, ZonaService
from shared.dtos import OpcionOut
from transportista.dtos import (
    ConceptoAdicionalOut,
    TarifarioOpcionesOut,
    TransportistaOpcionOut,
    UbicacionOpcionOut,
    ZonaOpcionOut,
)
from transportista.enums import MODALIDAD_FLETE_CHOICES
from transportista.services import ConceptoAdicionalService, TransportistaService


class OpcionesTarifarioUseCase:
    @staticmethod
    def execute() -> TarifarioOpcionesOut:
        return TarifarioOpcionesOut(
            modalidades=OpcionOut.desde_choices(MODALIDAD_FLETE_CHOICES),
            tipos_camion=OpcionOut.desde_choices(TIPO_CAMION_CHOICES),
            transportistas=[
                TransportistaOpcionOut.from_model(t)
                for t in TransportistaService.list_transportistas()
            ],
            conceptos=[
                ConceptoAdicionalOut.from_model(c)
                for c in ConceptoAdicionalService.list_conceptos()
            ],
            zonas=[ZonaOpcionOut.from_model(z) for z in ZonaService.list_zonas_para_opciones()],
            ubicaciones=[
                UbicacionOpcionOut.from_model(u)
                for u in UbicacionService.list_ubicaciones_para_opciones()
            ],
        )
