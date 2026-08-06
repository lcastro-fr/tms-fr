from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from catalog.paises import PAISES
from catalog.services import PaisService


class Command(BaseCommand):
    help = "Materializa catalog.paises.PAISES en la tabla pais. Idempotente por codigo."

    def handle(self, *args: Any, **options: Any) -> None:
        creados, actualizados = PaisService.sincronizar(PAISES)
        self.stdout.write(f"países: {creados} creados, {actualizados} actualizados")
