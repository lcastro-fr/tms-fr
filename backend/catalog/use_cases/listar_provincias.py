from __future__ import annotations

from catalog.dtos import ProvinciaOut
from catalog.services import DivisionService


class ListarProvinciasUseCase:
    @staticmethod
    def execute() -> list[ProvinciaOut]:
        return [
            ProvinciaOut.from_model(
                provincia,
                cantidad_departamentos=provincia.cantidad_departamentos,  # type: ignore[attr-defined]
            )
            for provincia in DivisionService.list_provincias()
        ]
