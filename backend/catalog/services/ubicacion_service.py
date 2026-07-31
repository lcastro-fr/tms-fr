from __future__ import annotations

from catalog.models import Ubicacion
from shared.exceptions import NotFoundError


class UbicacionService:
    class UbicacionNotFoundError(NotFoundError):
        pass

    @staticmethod
    def get_ubicacion_by_codigo(codigo: str) -> Ubicacion | None:
        return Ubicacion.objects.filter(codigo=codigo).first()

    @staticmethod
    def get_ubicacion_by_codigo_or_raise(codigo: str) -> Ubicacion:
        ubicacion = UbicacionService.get_ubicacion_by_codigo(codigo)
        if ubicacion is None:
            raise UbicacionService.UbicacionNotFoundError(
                f"No se encontró la ubicación con código {codigo}",
                detail={"codigo": codigo},
            )
        return ubicacion

    @staticmethod
    def resolve_codigos(codigos: list[str]) -> tuple[list[Ubicacion], list[str]]:
        encontradas = Ubicacion.objects.filter(codigo__in=codigos)
        por_codigo = {u.codigo: u for u in encontradas}
        faltantes = [c for c in codigos if c not in por_codigo]
        return [por_codigo[c] for c in codigos if c in por_codigo], faltantes
