from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from catalog.enums import PAIS_LOCAL, SRID_WGS84, DestinoDefault, TipoUbicacion
from catalog.models import Ubicacion
from catalog.services import PaisService

UBICACIONES: list[dict[str, Any]] = [
    {
        "codigo": "PL01",
        "tipo": TipoUbicacion.PLANTA.value,
        "nombre": "Planta San Nicolás",
        "calle": "Ruta 9 Km 232",
        "localidad": "San Nicolás",
        "provincia": "Buenos Aires",
    },
    {
        "codigo": "CL100",
        "tipo": TipoUbicacion.CLIENTE.value,
        "nombre": "Cliente Rosario Centro",
        "calle": "Córdoba 1500",
        "localidad": "Rosario",
        "provincia": "Santa Fe",
    },
    {
        "codigo": "CL200",
        "tipo": TipoUbicacion.CLIENTE.value,
        "nombre": "Cliente Córdoba Sur",
        "calle": "Av. Vélez Sarsfield 200",
        "localidad": "Córdoba",
        "provincia": "Córdoba",
    },
    {
        "codigo": "ARBUE",
        "tipo": TipoUbicacion.PUERTO.value,
        "nombre": "Puerto de Buenos Aires",
        "calle": "Av. Ramón Castillo s/n",
        "localidad": "Ciudad Autónoma de Buenos Aires",
        "provincia": "Buenos Aires",
        "destino_default": DestinoDefault.PUERTO_MARITIMO.value,
        "coordinates": Point(-58.3700, -34.5750, srid=SRID_WGS84),
    },
    {
        "codigo": "AREZE",
        "tipo": TipoUbicacion.AEROPUERTO.value,
        "nombre": "Aeropuerto Internacional de Ezeiza",
        "calle": "Autopista Teniente General Ricchieri Km 33,5",
        "localidad": "Ezeiza",
        "provincia": "Buenos Aires",
        "destino_default": DestinoDefault.AEROPUERTO.value,
        "coordinates": Point(-58.5358, -34.8222, srid=SRID_WGS84),
    },
]


class Command(BaseCommand):
    help = "Crea ubicaciones de prueba para poder probar la ingesta de tickets."

    def handle(self, *args: Any, **options: Any) -> None:
        pais = PaisService.get_pais_or_raise(PAIS_LOCAL)

        for datos in UBICACIONES:
            ubicacion, creada = Ubicacion.objects.get_or_create(
                codigo=datos["codigo"], defaults={**datos, "pais": pais}
            )
            estado = "creada" if creada else "ya existía"
            self.stdout.write(f"{ubicacion.codigo:>6}  {estado}  {ubicacion.nombre}")

        self.stdout.write(self.style.SUCCESS("Listo."))
