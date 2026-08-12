from __future__ import annotations

from enum import StrEnum

SRID_WGS84 = 4326

PAIS_LOCAL = "AR"

TOLERANCIA_ZONA = 0.001
TOLERANCIA_DISPLAY = 0.005


class DestinoDefault(StrEnum):
    PUERTO_MARITIMO = "puerto_maritimo"
    AEROPUERTO = "aeropuerto"


class TipoUbicacion(StrEnum):
    PLANTA = "planta"
    PUERTO = "puerto"
    AEROPUERTO = "aeropuerto"
    CLIENTE = "cliente"
    EXPRESO = "expreso"
    OTRO = "otro"


class TipoCamion(StrEnum):
    CHASIS = "chasis"
    BALANCIN = "balancin"
    SEMI = "semi"


TIPO_UBICACION_CHOICES = [(t.value, t.name.title()) for t in TipoUbicacion]
TIPO_CAMION_CHOICES = [(t.value, t.name.title()) for t in TipoCamion]
DESTINO_DEFAULT_CHOICES = [(d.value, d.name.replace("_", " ").title()) for d in DestinoDefault]
