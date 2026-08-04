from __future__ import annotations

from enum import StrEnum


class ModalidadFlete(StrEnum):
    DIRECTO = "directo"
    MULTIPARADA = "multiparada"

    @classmethod
    def para_destinos(cls, cantidad: int) -> ModalidadFlete:
        return cls.DIRECTO if cantidad <= 1 else cls.MULTIPARADA


class ConceptoUnidadMedida(StrEnum):
    DIA = "dia"
    HORA = "hora"


class TipoOperacion(StrEnum):
    CARGA = "carga"
    CAMARA = "camara"


MODALIDAD_FLETE_CHOICES = [(m.value, m.name.title()) for m in ModalidadFlete]
CONCEPTO_UNIDAD_MEDIDA_CHOICES = [(u.value, u.name.title()) for u in ConceptoUnidadMedida]
TIPO_OPERACION_CHOICES = [(t.value, t.name.title()) for t in TipoOperacion]
