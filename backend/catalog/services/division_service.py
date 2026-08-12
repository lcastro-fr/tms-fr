from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.gis.db.models import Union as UnionGeom
from django.contrib.gis.geos import MultiPolygon
from django.db.models import Count, Q, Sum

from catalog.enums import TOLERANCIA_ZONA
from catalog.models import Departamento, Provincia
from catalog.services.zona_service import ZonaService
from shared.exceptions import BusinessRuleError, NotFoundError


class DivisionService:
    class ProvinciaNotFoundError(NotFoundError):
        pass

    class DivisionNoEncontradaError(BusinessRuleError):
        pass

    @staticmethod
    def list_provincias() -> list[Provincia]:
        return list(
            Provincia.objects.annotate(
                cantidad_departamentos=Count("departamentos", filter=Q(departamentos__active=True))
            ).order_by("nombre")
        )

    @staticmethod
    def get_provincia(codigo: str) -> Provincia | None:
        return Provincia.objects.filter(pk=codigo.strip()).first()

    @staticmethod
    def get_provincia_or_raise(codigo: str) -> Provincia:
        provincia = DivisionService.get_provincia(codigo)
        if provincia is None:
            raise DivisionService.ProvinciaNotFoundError(
                f"No existe la provincia con código {codigo!r}",
                detail={"codigo": codigo},
            )
        return provincia

    @staticmethod
    def list_departamentos(provincia: Provincia) -> list[Departamento]:
        return list(Departamento.objects.filter(provincia=provincia))

    @staticmethod
    def union_de(provincias: list[str], departamentos: list[str]) -> tuple[MultiPolygon, Decimal]:
        """
        Une las divisiones marcadas y devuelve (geometría simplificada, superficie declarada).

        La unión sale de `geom` completa: `geom_display` existe sólo para dibujar el selector.
        """
        DivisionService._check_existen(Provincia, provincias)
        DivisionService._check_existen(Departamento, departamentos)

        parciales = []
        if provincias:
            parciales.append(
                Provincia.objects.filter(pk__in=provincias).aggregate(u=UnionGeom("geom"))["u"]
            )
        if departamentos:
            parciales.append(
                Departamento.objects.filter(pk__in=departamentos).aggregate(u=UnionGeom("geom"))[
                    "u"
                ]
            )

        union = parciales[0]
        for otra in parciales[1:]:
            union = union.union(otra)

        # simplify puede colapsar el MultiPolygon a Polygon, y la columna no lo acepta.
        simple = union.simplify(TOLERANCIA_ZONA, preserve_topology=True)
        if simple.geom_type == "Polygon":
            simple = MultiPolygon(simple)
        simple.srid = union.srid
        ZonaService._check_geom(simple)

        return simple, DivisionService._superficie(provincias, departamentos)

    @staticmethod
    def _check_existen(modelo: type[Provincia] | type[Departamento], codigos: list[str]) -> None:
        if not codigos:
            return
        existentes = set(modelo.objects.filter(pk__in=codigos).values_list("pk", flat=True))
        faltantes = sorted(set(codigos) - existentes)
        if faltantes:
            raise DivisionService.DivisionNoEncontradaError(
                f"No existen estas divisiones: {', '.join(faltantes)}",
                detail={"codigos": faltantes},
            )

    @staticmethod
    def _superficie(provincias: list[str], departamentos: list[str]) -> Decimal:
        """
        Suma la superficie declarada por el INDEC, no la del polígono simplificado.

        Un departamento de una provincia ya marcada entera no se cuenta dos veces.
        """
        total = Decimal(0)
        if provincias:
            total += Provincia.objects.filter(pk__in=provincias).aggregate(s=Sum("superficie_km2"))[
                "s"
            ] or Decimal(0)
        if departamentos:
            total += Departamento.objects.filter(pk__in=departamentos).exclude(
                provincia_id__in=provincias
            ).aggregate(s=Sum("superficie_km2"))["s"] or Decimal(0)
        return total

    @staticmethod
    def sincronizar_provincias(filas: list[dict[str, Any]]) -> tuple[int, int]:
        return DivisionService._sincronizar(Provincia, filas)

    @staticmethod
    def sincronizar_departamentos(filas: list[dict[str, Any]]) -> tuple[int, int]:
        return DivisionService._sincronizar(Departamento, filas)

    @staticmethod
    def _sincronizar(
        modelo: type[Provincia] | type[Departamento], filas: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Devuelve (creados, actualizados). Idempotente por código."""
        creados = actualizados = 0
        for fila in filas:
            campos = dict(fila)
            codigo = campos.pop("codigo")
            _, creado = modelo.all_objects.update_or_create(
                codigo=codigo, defaults={**campos, "active": True}
            )
            if creado:
                creados += 1
            else:
                actualizados += 1
        return creados, actualizados
