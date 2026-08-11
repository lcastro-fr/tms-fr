from __future__ import annotations

from django.db import transaction

from catalog.dtos import UbicacionCrearIn, UbicacionOut
from catalog.services import PaisService, UbicacionService
from shared.exceptions import BusinessRuleError


class CrearUbicacionUseCase:
    class PaisInvalidoError(BusinessRuleError):
        pass

    @staticmethod
    @transaction.atomic
    def execute(data: UbicacionCrearIn) -> UbicacionOut:
        pais = PaisService.get_pais(data.pais_codigo)
        if pais is None:
            # 422 y no el 404 de get_pais_or_raise: un 404 acá se lee como "no existe la
            # ubicación", que es otra cosa.
            raise CrearUbicacionUseCase.PaisInvalidoError(
                f"No existe el país con código {data.pais_codigo!r}",
                detail={"campo": "pais_codigo", "codigo": data.pais_codigo},
            )

        lng, lat = data.coordinates.coordinates
        ubicacion = UbicacionService.create_ubicacion(
            nombre=data.nombre,
            tipo=data.tipo.value,
            codigo=data.codigo,
            calle=data.calle,
            localidad=data.localidad,
            provincia=data.provincia,
            pais=pais,
            lat=lat,
            lng=lng,
        )
        return UbicacionOut.from_model(ubicacion)
