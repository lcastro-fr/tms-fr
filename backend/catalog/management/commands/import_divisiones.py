from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from django.conf import settings
from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.enums import TOLERANCIA_DISPLAY
from catalog.services import DivisionService

SEED_DIR = Path(settings.BASE_DIR) / "seed"
DEFAULT_PROVINCIAS = SEED_DIR / "Provincias (2022).csv"
DEFAULT_DEPARTAMENTOS = SEED_DIR / "Departamentos (2022).csv"

COL_CODIGO = "Código"
COL_NOMBRE = "Nombre"
COL_PROVINCIA = "Código de provincia"
COL_SUPERFICIE = "Superficie en km2"
COL_GEOM = "Geometría en GeoJSON"

REQUIRED_PROVINCIAS = (COL_CODIGO, COL_NOMBRE, COL_SUPERFICIE, COL_GEOM)
REQUIRED_DEPARTAMENTOS = (*REQUIRED_PROVINCIAS, COL_PROVINCIA)

# Las filas traen hasta ~500 KB de GeoJSON en un solo campo; el default son 131.072 bytes.
csv.field_size_limit(10**9)


class _DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Importa provincias y departamentos del INDEC desde CSV. Idempotente por código."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--file-provincias", type=Path, default=DEFAULT_PROVINCIAS)
        parser.add_argument("--file-departamentos", type=Path, default=DEFAULT_DEPARTAMENTOS)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        provincias = self._leer(options["file_provincias"], REQUIRED_PROVINCIAS)
        departamentos = self._leer(options["file_departamentos"], REQUIRED_DEPARTAMENTOS)

        errores: list[str] = []
        discrepancias: list[str] = []
        resultado: dict[str, tuple[int, int]] = {}

        filas_prov = self._parsear(provincias, errores, discrepancias, largo_codigo=2)
        filas_dep = self._parsear(departamentos, errores, discrepancias, largo_codigo=5)

        if not errores:
            try:
                with transaction.atomic():
                    resultado["provincias"] = DivisionService.sincronizar_provincias(filas_prov)
                    resultado["departamentos"] = DivisionService.sincronizar_departamentos(
                        filas_dep
                    )
                    if options["dry_run"]:
                        raise _DryRun
            except _DryRun:
                pass

        self._report(resultado, len(filas_prov), len(filas_dep), errores, discrepancias, options)

    @staticmethod
    def _leer(path: Path, requeridas: tuple[str, ...]) -> list[dict[str, str]]:
        if not path.exists():
            raise CommandError(f"No existe {path}")
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            faltantes = [c for c in requeridas if c not in (reader.fieldnames or [])]
            if faltantes:
                raise CommandError(f"{path.name}: faltan columnas {', '.join(faltantes)}")
            filas = list(reader)
        if not filas:
            raise CommandError(f"{path.name}: sin filas de datos")
        return filas

    def _parsear(
        self,
        filas: list[dict[str, str]],
        errores: list[str],
        discrepancias: list[str],
        largo_codigo: int,
    ) -> list[dict[str, Any]]:
        salida: list[dict[str, Any]] = []
        for numero, fila in enumerate(filas, start=2):
            codigo = (fila.get(COL_CODIGO) or "").strip()
            nombre = (fila.get(COL_NOMBRE) or "").strip()
            if len(codigo) != largo_codigo:
                errores.append(f"fila {numero}: código {codigo!r} no tiene {largo_codigo} dígitos")
                continue
            if not nombre:
                errores.append(f"fila {numero} ({codigo}): sin nombre")
                continue

            try:
                superficie = Decimal((fila.get(COL_SUPERFICIE) or "").strip())
            except (InvalidOperation, ValueError):
                errores.append(f"fila {numero} ({codigo}): superficie ilegible")
                continue

            geom = self._geometria(fila.get(COL_GEOM))
            if geom is None:
                errores.append(f"fila {numero} ({codigo}): geometría ilegible o no poligonal")
                continue

            campos: dict[str, Any] = {
                "codigo": codigo,
                "nombre": nombre,
                "superficie_km2": superficie.quantize(Decimal("0.0001")),
                "geom": geom,
                "geom_display": self._simplificar(geom),
            }

            if largo_codigo > 2:
                # El código propio manda: la columna del CSV tiene errores conocidos
                # (30105 Victoria viene como Santa Fe cuando su código dice Entre Ríos).
                campos["provincia_id"] = codigo[:2]
                declarada = (fila.get(COL_PROVINCIA) or "").strip()
                if declarada and declarada != codigo[:2]:
                    discrepancias.append(
                        f"{codigo} {nombre}: el CSV la pone en {declarada}, el código dice "
                        f"{codigo[:2]}"
                    )

            salida.append(campos)
        return salida

    @staticmethod
    def _geometria(crudo: str | None) -> MultiPolygon | None:
        if not crudo:
            return None
        try:
            geom = GEOSGeometry(json.dumps(json.loads(crudo)))
        except (GDALException, GEOSException, ValueError, TypeError):
            return None
        # Los CSV traen los dos tipos; la columna sólo acepta MultiPolygon.
        if geom.geom_type == "Polygon":
            return MultiPolygon(geom, srid=geom.srid)
        if geom.geom_type == "MultiPolygon":
            return cast("MultiPolygon", geom)
        return None

    @staticmethod
    def _simplificar(geom: MultiPolygon) -> MultiPolygon:
        simple = geom.simplify(TOLERANCIA_DISPLAY, preserve_topology=True)
        if simple.geom_type == "Polygon":
            return MultiPolygon(simple, srid=geom.srid)
        return cast("MultiPolygon", simple)

    def _report(
        self,
        resultado: dict[str, tuple[int, int]],
        leidas_prov: int,
        leidas_dep: int,
        errores: list[str],
        discrepancias: list[str],
        options: dict[str, Any],
    ) -> None:
        self.stdout.write(f"provincias: {leidas_prov} filas, departamentos: {leidas_dep} filas")
        for nivel, (creados, actualizados) in resultado.items():
            self.stdout.write(f"  {nivel:15}: {creados} creados, {actualizados} actualizados")
        if options["dry_run"] and resultado:
            self.stdout.write(self.style.WARNING("  dry-run: se revirtió todo"))

        if discrepancias:
            self.stdout.write(
                self.style.WARNING(
                    f"  provincia declarada distinta del código: {len(discrepancias)} "
                    f"(gana el código)"
                )
            )
            for linea in discrepancias[:10]:
                self.stdout.write(f"    {linea}")

        if errores:
            self.stdout.write(self.style.ERROR(f"  descartadas: {len(errores)}"))
            for linea in errores[:20]:
                self.stdout.write(f"    {linea}")
            raise CommandError(f"{len(errores)} filas descartadas, no se escribió nada")

        self.stdout.write(self.style.SUCCESS("Listo."))
