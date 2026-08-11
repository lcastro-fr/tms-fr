from __future__ import annotations

from enum import StrEnum

from catalog.enums import DestinoDefault
from transportista.enums import TipoOperacion, Via

DESTINO_DEFAULT_POR_VIA = {
    Via.MARITIMA: DestinoDefault.PUERTO_MARITIMO,
    Via.AEREA: DestinoDefault.AEROPUERTO,
}


class OrigenDestinos(StrEnum):
    EXPLICITOS = "explicitos"
    REMITOS = "remitos"
    NO_APLICA = "no_aplica"

    @classmethod
    def para(cls, tipo_operacion: str, tiene_explicitos: bool) -> OrigenDestinos:
        if tipo_operacion == TipoOperacion.CAMARA.value:
            return cls.NO_APLICA
        return cls.EXPLICITOS if tiene_explicitos else cls.REMITOS


ORIGEN_DESTINOS_CHOICES = [(o.value, o.name.replace("_", " ").title()) for o in OrigenDestinos]
