from __future__ import annotations

from enum import StrEnum


class ModalidadFlete(StrEnum):
    DIRECTO = 'directo'
    MULTIPARADA = 'multiparada'

    @classmethod
    def para_destinos(cls, cantidad: int) -> ModalidadFlete:
        return cls.DIRECTO if cantidad <= 1 else cls.MULTIPARADA

class ConceptoUnidadMedida(StrEnum):
    DIA = 'dia'
    HORA = 'hora'

MODALIDAD_FLETE_CHOICES = [(m.value, m.name.title()) for m in ModalidadFlete]
CONCEPTO_UNIDAD_MEDIDA_CHOICES = [(u.value, u.name.title()) for u in ConceptoUnidadMedida]
