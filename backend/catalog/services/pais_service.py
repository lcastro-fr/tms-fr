from __future__ import annotations

from catalog.models import Pais
from shared.exceptions import NotFoundError


class PaisService:
    class PaisNotFoundError(NotFoundError):
        pass

    @staticmethod
    def list_paises() -> list[Pais]:
        return list(Pais.objects.order_by("nombre"))

    @staticmethod
    def get_pais(codigo: str) -> Pais | None:
        return Pais.objects.filter(pk=codigo.strip().upper()).first()

    @staticmethod
    def get_pais_or_raise(codigo: str) -> Pais:
        pais = PaisService.get_pais(codigo)
        if pais is None:
            raise PaisService.PaisNotFoundError(
                f"No existe el país con código {codigo!r}",
                detail={"codigo": codigo},
            )
        return pais

    @staticmethod
    def resolve(valor: str | None) -> Pais | None:
        """Resuelve por código o, si no matchea, por nombre. SAP manda el código."""
        if not valor:
            return None
        limpio = valor.strip()
        return PaisService.get_pais(limpio) or Pais.objects.filter(nombre__iexact=limpio).first()

    @staticmethod
    def sincronizar(paises: list[tuple[str, str]]) -> tuple[int, int]:
        """Devuelve (creados, actualizados). Idempotente por código."""
        creados = actualizados = 0
        for codigo, nombre in paises:
            _, creado = Pais.all_objects.update_or_create(
                codigo=codigo, defaults={"nombre": nombre, "active": True}
            )
            if creado:
                creados += 1
            else:
                actualizados += 1
        return creados, actualizados
