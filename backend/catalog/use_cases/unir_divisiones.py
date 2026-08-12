from __future__ import annotations

from catalog.dtos import UnionDivisionesIn, UnionDivisionesOut, multipolygon_out
from catalog.services import DivisionService


class UnirDivisionesUseCase:
    """Preview: no escribe nada, igual que GeocodificarUbicacionUseCase."""

    @staticmethod
    def execute(data: UnionDivisionesIn) -> UnionDivisionesOut:
        geom, superficie = DivisionService.union_de(data.provincias, data.departamentos)
        return UnionDivisionesOut(
            geom=multipolygon_out(geom),
            poligonos=geom.num_geom,
            vertices=geom.num_points,
            superficie_km2=superficie,
        )
