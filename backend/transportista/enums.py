from __future__ import annotations

from enum import StrEnum

class EstadoTarifario(StrEnum):
    VIGENTE = 'vigente'
    CERRADO = 'cerrado'

class ModalidadFlete(StrEnum):
    DIRECTO = 'directo'
    MULTIPARADA = 'multiparada'

class ConceptoUnidadMedida(StrEnum):
    DIA = 'dia'
    HORA = 'hora'

ESTADO_TARIFARIO_CHOICES = [(t.value, t.name.title()) for t in EstadoTarifario]
MODALIDAD_FLETE_CHOICES = [(m.value, m.name.title()) for m in ModalidadFlete]
CONCEPTO_UNIDAD_MEDIDA_CHOICES = [(u.value, u.name.title()) for u in ConceptoUnidadMedida]
