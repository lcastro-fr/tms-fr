from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from transportista.models import Transportista


class TransportistaIn(BaseModel):
    cuit: str = Field(min_length=11, max_length=13)
    razon_social: str = Field(min_length=1, max_length=200)


class TransportistaOut(BaseModel):
    id: int
    cuit: str
    razon_social: str

    @classmethod
    def from_model(cls, transportista: Transportista) -> TransportistaOut:
        return cls(
            id=transportista.id,
            cuit=transportista.cuit,
            razon_social=transportista.razon_social,
        )
