from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_COUNTRIES = {"AR": "Argentina"}

_PAISES_ACEPTADOS = dict(SUPPORTED_COUNTRIES) | {
    nombre.upper(): nombre for nombre in SUPPORTED_COUNTRIES.values()
}


def normalizar_pais(pais: str) -> str | None:
    return _PAISES_ACEPTADOS.get(pais.strip().upper())


class Coordinate(BaseModel):
    model_config = ConfigDict(frozen=True)

    lat: Decimal = Field(ge=-90, le=90)
    lng: Decimal = Field(ge=-180, le=180)

    @classmethod
    def from_lnglat(cls, lng: float | str, lat: float | str) -> Coordinate:
        """Build from a GeoJSON/ORS ``[lng, lat]`` pair."""
        return cls(lat=Decimal(str(lat)), lng=Decimal(str(lng)))

    def to_lnglat(self) -> list[float]:
        """Render as a GeoJSON/ORS ``[lng, lat]`` pair."""
        return [float(self.lng), float(self.lat)]


class GeocodeQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    direccion: str
    localidad: str
    provincia: str
    pais: str

    @field_validator("pais", mode="after")
    @classmethod
    def clean_pais(cls, value: str) -> str:
        return value.strip()

    @field_validator("localidad", mode="after")
    @classmethod
    def clean_localidad(cls, value: str) -> str:
        # A veces viene con la provincia incluida...
        return value.split("-")[0].strip()

    def as_text(self) -> str:
        parts = [self.direccion, self.localidad, self.provincia, self.pais]
        return ", ".join(p for p in parts)
