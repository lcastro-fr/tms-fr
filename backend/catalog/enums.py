from __future__ import annotations

from enum import StrEnum

SRID_WGS84 = 4326


class TipoUbicacion(StrEnum):
    PLANTA = "planta"
    PUERTO = "puerto"
    AEROPUERTO = "aeropuerto"
    CLIENTE = "cliente"
    OTRO = "otro"


class TipoCamion(StrEnum):
    CHASIS = "chasis"
    BALANCIN = "balancin"
    SEMI = "semi"


TIPO_UBICACION_CHOICES = [(t.value, t.name.title()) for t in TipoUbicacion]
TIPO_CAMION_CHOICES = [(t.value, t.name.title()) for t in TipoCamion]
