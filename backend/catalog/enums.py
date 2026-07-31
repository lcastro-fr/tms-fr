from __future__ import annotations

from enum import StrEnum


class TipoUbicacion(StrEnum):
    PLANTA = "planta"
    PUERTO = "puerto"
    AEROPUERTO = "aeropuerto"
    CLIENTE = "cliente"
    OTRO = "otro"


TIPO_UBICACION_CHOICES = [(t.value, t.name.title()) for t in TipoUbicacion]
