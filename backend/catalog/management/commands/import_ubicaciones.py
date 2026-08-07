from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.enums import PAIS_LOCAL
from catalog.services import PaisService, UbicacionService
from shared.exceptions import DomainError
from shared.xlsx import read_rows

DEFAULT_FILE = Path(settings.BASE_DIR) / "seed" / "locales.xlsx"

REQUIRED_COLUMNS = ("code", "type", "name", "street", "province", "lat", "long")

# Solo para avisar, no para rechazar: un cliente de exportacion puede caer afuera.
AR_LNG_MIN, AR_LAT_MIN, AR_LNG_MAX, AR_LAT_MAX = -74.0, -56.0, -53.0, -21.0


class _DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Importa ubicaciones con coordenadas desde un xlsx. Idempotente por codigo."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        path: Path = options["file"]
        if not path.exists():
            raise CommandError(f"No existe {path}")

        rows = read_rows(path)
        if not rows:
            raise CommandError(f"{path}: sin filas de datos")

        columnas = set().union(*(r.keys() for r in rows))
        faltantes = [c for c in REQUIRED_COLUMNS if c not in columnas]
        if faltantes:
            raise CommandError(f"{path}: faltan columnas {', '.join(faltantes)}")

        creados = actualizados = 0
        errores: list[str] = []
        fuera_bbox: list[str] = []
        sin_pais: list[str] = []
        paises: dict[str, Any] = {}

        try:
            with transaction.atomic():
                for numero, row in enumerate(rows, start=2):
                    codigo = row.get("code")
                    if not codigo:
                        errores.append(f"fila {numero}: sin code")
                        continue

                    lat, lng, error = self._parse_coords(row)
                    if error:
                        errores.append(f"fila {numero} ({codigo}): {error}")
                        continue

                    if lat is not None and lng is not None and not self._en_argentina(lat, lng):
                        nombre = (row.get("name") or "")[:30]
                        fuera_bbox.append(f"{codigo} {nombre} ({lat:.4f}, {lng:.4f})")

                    provincia = row.get("province") or ""
                    if provincia == "0":
                        provincia = ""

                    crudo = row.get("country") or PAIS_LOCAL
                    if crudo not in paises:
                        paises[crudo] = PaisService.resolve(crudo)
                    pais = paises[crudo]
                    if pais is None:
                        sin_pais.append(f"{codigo} ({crudo})")

                    try:
                        # Savepoint propio: sin esto, un DomainError dejaría la
                        # transacción externa envenenada y no se podría seguir.
                        with transaction.atomic():
                            _, creada = UbicacionService.upsert_by_codigo(
                                codigo=codigo,
                                tipo=(row.get("type") or "").lower(),
                                nombre=row.get("name") or "",
                                calle=row.get("street") or "",
                                localidad=row.get("locality") or "",
                                provincia=provincia,
                                pais=pais,
                                lat=lat,
                                lng=lng,
                            )
                    except DomainError as exc:
                        errores.append(f"fila {numero} ({codigo}): {exc.message}")
                        continue

                    if creada:
                        creados += 1
                    else:
                        actualizados += 1

                if options["dry_run"]:
                    raise _DryRun
        except _DryRun:
            pass

        self._report(path, len(rows), creados, actualizados, errores, fuera_bbox, sin_pais, options)

    @staticmethod
    def _parse_coords(row: dict[str, str]) -> tuple[float | None, float | None, str | None]:
        raw_lat, raw_lng = row.get("lat"), row.get("long")
        if not raw_lat and not raw_lng:
            return None, None, None
        try:
            return float(raw_lat), float(raw_lng), None  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, None, f"lat/long ilegibles ({raw_lat!r}, {raw_lng!r})"

    @staticmethod
    def _en_argentina(lat: float, lng: float) -> bool:
        return AR_LNG_MIN <= lng <= AR_LNG_MAX and AR_LAT_MIN <= lat <= AR_LAT_MAX

    def _report(
        self,
        path: Path,
        leidas: int,
        creados: int,
        actualizados: int,
        errores: list[str],
        fuera_bbox: list[str],
        sin_pais: list[str],
        options: dict[str, Any],
    ) -> None:
        self.stdout.write(f"{path.name}: {leidas} filas leídas")
        if options["dry_run"]:
            self.stdout.write(f"  validadas        : {creados + actualizados}")
            self.stdout.write(self.style.WARNING("  dry-run: se revirtió todo"))
        else:
            self.stdout.write(f"  creadas          : {creados}")
            self.stdout.write(f"  actualizadas     : {actualizados}")

        if fuera_bbox:
            self.stdout.write(
                self.style.WARNING(f"  fuera de Argentina: {len(fuera_bbox)} (se importan igual)")
            )
            for linea in fuera_bbox[:10]:
                self.stdout.write(f"    {linea}")

        if sin_pais:
            self.stdout.write(
                self.style.WARNING(f"  sin país resuelto : {len(sin_pais)} (se importan sin país)")
            )
            for linea in sin_pais[:10]:
                self.stdout.write(f"    {linea}")

        if errores:
            self.stdout.write(self.style.ERROR(f"  descartadas      : {len(errores)}"))
            for linea in errores[:20]:
                self.stdout.write(f"    {linea}")
            raise CommandError(f"{len(errores)} filas descartadas")

        self.stdout.write(self.style.SUCCESS("Listo."))
