from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from catalog.enums import TipoUbicacion
from catalog.models import Ubicacion

UBICACIONES = [
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
]


class Command(BaseCommand):
    help = "Crea ubicaciones de prueba para poder probar la ingesta de tickets."

    def handle(self, *args: Any, **options: Any) -> None:
        for datos in UBICACIONES:
            ubicacion, creada = Ubicacion.objects.get_or_create(
                codigo=datos["codigo"], defaults=datos
            )
            estado = "creada" if creada else "ya existía"
            self.stdout.write(f"{ubicacion.codigo:>6}  {estado}  {ubicacion.nombre}")

        self.stdout.write(self.style.SUCCESS("Listo."))
