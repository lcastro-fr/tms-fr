from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from catalog.enums import TipoUbicacion
from shared.dtos import OpcionOut

if TYPE_CHECKING:
    from catalog.models import Pais, Ubicacion, Zona

CodigoUbicacion = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]

# Contra columnas NOT NULL: sin max_length un campo largo es un DataError → 500 en vez de 422.
CalleUbicacion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
LocalidadUbicacion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
CodigoPais = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=2, max_length=2)
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


class UbicacionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    tipo: TipoUbicacion
    coordinates: GeoJSONPoint


class UbicacionCrearIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    tipo: TipoUbicacion
    codigo: CodigoUbicacion | None = None
    calle: CalleUbicacion
    localidad: LocalidadUbicacion
    provincia: LocalidadUbicacion
    pais_codigo: CodigoPais
    coordinates: GeoJSONPoint

    @field_validator("codigo", mode="before")
    @classmethod
    def blanco_es_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def planta_exige_codigo(self) -> Self:
        if self.tipo is TipoUbicacion.PLANTA and self.codigo is None:
            raise ValueError("Una planta necesita código para que la ingesta pueda encontrarla")
        return self


class GeocodificarUbicacionIn(BaseModel):
    calle: str | None = Field(default=None, max_length=200)
    localidad: str | None = Field(default=None, max_length=120)
    provincia: str | None = Field(default=None, max_length=120)
    pais_codigo: CodigoPais

    @model_validator(mode="after")
    def al_menos_una_parte(self) -> Self:
        if not any(p and p.strip() for p in (self.calle, self.localidad, self.provincia)):
            raise ValueError("Completá al menos la calle, la localidad o la provincia")
        return self


class UbicacionGeocodificadaOut(BaseModel):
    coordinates: GeoJSONPoint
    consulta: str


class PaisOpcionOut(BaseModel):
    codigo: str
    nombre: str

    @classmethod
    def from_model(cls, pais: Pais) -> PaisOpcionOut:
        return cls(codigo=pais.codigo, nombre=pais.nombre)


class UbicacionOpcionesOut(BaseModel):
    tipos_ubicacion: list[OpcionOut]
    paises: list[PaisOpcionOut]

    @classmethod
    def from_choices(
        cls, tipos_ubicacion: list[tuple[str, str]], paises: list[Pais]
    ) -> UbicacionOpcionesOut:
        return cls(
            tipos_ubicacion=OpcionOut.desde_choices(tipos_ubicacion),
            paises=[PaisOpcionOut.from_model(p) for p in paises],
        )


class UbicacionesFilters(BaseModel):
    validada: bool | None = None
    con_coordenadas: bool | None = None


class UbicacionOpcionOut(BaseModel):
    id: int
    codigo: str | None
    nombre: str
    tipo: str
    localidad: str | None
    provincia: str | None
    pais: str | None
    tiene_coordenadas: bool

    @classmethod
    def from_model(cls, ubicacion: Ubicacion) -> UbicacionOpcionOut:
        return cls(
            id=ubicacion.id,
            codigo=ubicacion.codigo,
            nombre=ubicacion.nombre,
            tipo=ubicacion.tipo,
            localidad=ubicacion.localidad,
            provincia=ubicacion.provincia,
            pais=ubicacion.pais.nombre if ubicacion.pais else None,
            tiene_coordenadas=ubicacion.tiene_coordenadas,  # type: ignore[attr-defined]
        )


class UbicacionOut(BaseModel):
    id: int
    tipo: str
    nombre: str
    codigo: str | None
    calle: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    pais: str | None = None
    pais_codigo: str | None = None
    coordinates: GeoJSONPoint | None
    validada: bool
    destino_default: str | None = None

    @classmethod
    def from_model(cls, ubicacion: Ubicacion) -> UbicacionOut:
        punto = ubicacion.coordinates
        return cls(
            id=ubicacion.id,
            tipo=ubicacion.tipo,
            nombre=ubicacion.nombre,
            codigo=ubicacion.codigo,
            calle=ubicacion.calle,
            localidad=ubicacion.localidad,
            provincia=ubicacion.provincia,
            pais=ubicacion.pais.nombre if ubicacion.pais else None,
            pais_codigo=ubicacion.pais_id,
            coordinates=GeoJSONPoint(coordinates=[punto.x, punto.y]) if punto else None,
            validada=ubicacion.validada,
            destino_default=ubicacion.destino_default,
        )
