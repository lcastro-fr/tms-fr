from __future__ import annotations

from pydantic import BaseModel


class OpcionOut(BaseModel):
    value: str
    label: str

    @classmethod
    def desde_choices(cls, choices: list[tuple[str, str]]) -> list[OpcionOut]:
        return [cls(value=value, label=label) for value, label in choices]


class ErrorDetailOut(BaseModel):
    code: str
    message: str
    detail: dict = {}


class ErrorOut(BaseModel):
    error: ErrorDetailOut


ERRORS: dict[int, type[ErrorOut]] = {
    400: ErrorOut,
    401: ErrorOut,
    403: ErrorOut,
    404: ErrorOut,
    409: ErrorOut,
    422: ErrorOut,
    500: ErrorOut,
}
