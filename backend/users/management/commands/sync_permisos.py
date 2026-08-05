from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from users.services import PermisoService


class _DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Sincroniza la tabla permiso con PermisoCodigo. Idempotente."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        creados = actualizados = 0
        retirados: list[str] = []

        try:
            with transaction.atomic():
                creados, actualizados, retirados = PermisoService.sincronizar()
                if options["dry_run"]:
                    raise _DryRun
        except _DryRun:
            pass

        self._report(creados, actualizados, retirados, options)

    def _report(
        self,
        creados: int,
        actualizados: int,
        retirados: list[str],
        options: dict[str, Any],
    ) -> None:
        if options["dry_run"]:
            self.stdout.write(f"  validados     : {creados + actualizados}")
            self.stdout.write(self.style.WARNING("  dry-run: se revirtió todo"))
        else:
            self.stdout.write(f"  creados       : {creados}")
            self.stdout.write(f"  actualizados  : {actualizados}")

        if retirados:
            self.stdout.write(
                self.style.WARNING(f"  dados de baja : {len(retirados)} (ya no están en el enum)")
            )
            for codigo in retirados:
                self.stdout.write(f"    {codigo}")

        self.stdout.write(self.style.SUCCESS("Listo."))
