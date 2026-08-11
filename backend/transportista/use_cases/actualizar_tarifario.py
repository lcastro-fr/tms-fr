from __future__ import annotations

from django.db import transaction

from transportista.dtos import TarifarioDetalleOut, TarifarioIn
from transportista.services import TarifarioService


class ActualizarTarifarioUseCase:
    """
    Un tarifario en uso conserva sus filas congeladas y sus metadatos: sólo admite sumar
    tarifas nuevas. Si no está en uso, se reemplaza entero.
    """

    @staticmethod
    @transaction.atomic
    def execute(tarifario_id: int, data: TarifarioIn) -> TarifarioDetalleOut:
        tarifario = TarifarioService.get_tarifario_or_raise(tarifario_id)
        fletes = [f.model_dump() for f in data.tarifas_flete]
        conceptos = [c.model_dump() for c in data.tarifas_concepto]

        en_uso = TarifarioService.esta_en_uso(tarifario.id)
        if en_uso:
            TarifarioService.agregar_hijos(tarifario, fletes=fletes, conceptos=conceptos)
        else:
            tarifario = TarifarioService.update_tarifario(
                tarifario,
                transportista_id=data.transportista_id,
                vigente_desde=data.vigente_desde,
                vigente_hasta=data.vigente_hasta,
            )
            TarifarioService.replace_hijos(tarifario, fletes=fletes, conceptos=conceptos)

        fletes_out, conceptos_out = TarifarioService.get_hijos(tarifario.id)
        return TarifarioDetalleOut.from_model(
            tarifario, en_uso=en_uso, fletes=fletes_out, conceptos=conceptos_out
        )
