from __future__ import annotations

from transportista.services import TarifarioService


class EliminarTarifarioUseCase:
    @staticmethod
    def execute(tarifario_id: int) -> None:
        tarifario = TarifarioService.get_tarifario_or_raise(tarifario_id)
        if TarifarioService.esta_en_uso(tarifario.id):
            raise TarifarioService.TarifarioEnUsoError(
                "El tarifario ya se usó para costear una orden de servicio y no se puede dar "
                "de baja: cerrá su vigencia",
                detail={"tarifario_id": tarifario.id, "motivo": "en_uso"},
            )
        TarifarioService.delete_tarifario(tarifario)
