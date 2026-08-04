from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

if TYPE_CHECKING:
    from catalog.models import Zona

CodigoUbicacion = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]] = Field(min_length=1)


class ZonaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    geom: GeoJSONPolygon


class ZonaOut(BaseModel):
    id: int
    nombre: str
    active: bool
    geom: GeoJSONPolygon

    @classmethod
    def from_model(cls, zona: Zona) -> ZonaOut:
        # Desde .coords y no desde .json para no serializar y volver a parsear.
        return cls(
            id=zona.id,
            nombre=zona.nombre,
            active=zona.active,
            geom=GeoJSONPolygon(
                coordinates=[[list(punto) for punto in anillo] for anillo in zona.geom.coords]
            ),
        )
