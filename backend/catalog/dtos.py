from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

if TYPE_CHECKING:
    from catalog.models import Ubicacion, Zona

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


class GeoJSONPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(min_length=2, max_length=2)


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


class UbicacionOut(BaseModel):
    id: int
    tipo: str
    nombre: str
    codigo: str | None
    calle: str
    localidad: str
    provincia: str
    pais: str
    coordinates: GeoJSONPoint | None
    validada: bool

    @classmethod
    def from_model(cls, ubicacion: Ubicacion) -> UbicacionOut:
        # latitud/longitud son @property de Python y no viajarían solas.
        punto = ubicacion.coordinates
        return cls(
            id=ubicacion.id,
            tipo=ubicacion.tipo,
            nombre=ubicacion.nombre,
            codigo=ubicacion.codigo,
            calle=ubicacion.calle,
            localidad=ubicacion.localidad,
            provincia=ubicacion.provincia,
            pais=ubicacion.pais,
            coordinates=GeoJSONPoint(coordinates=[punto.x, punto.y]) if punto else None,
            validada=ubicacion.validada,
        )
