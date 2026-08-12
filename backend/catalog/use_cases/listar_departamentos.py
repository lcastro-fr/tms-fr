from __future__ import annotations

from catalog.dtos import DivisionOut
from catalog.services import DivisionService


class ListarDepartamentosUseCase:
    @staticmethod
    def execute(provincia_codigo: str) -> list[DivisionOut]:
        provincia = DivisionService.get_provincia_or_raise(provincia_codigo)
        return [
            DivisionOut.from_model(departamento)
            for departamento in DivisionService.list_departamentos(provincia)
        ]
