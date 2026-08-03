from __future__ import annotations

from django.contrib.gis.geos import Point, Polygon
from django.db import IntegrityError, transaction

from catalog.enums import SRID_WGS84
from catalog.models import Ubicacion, Zona
from shared.exceptions import BusinessRuleError, ConflictError


class ZonaService:
    class GeometriaInvalidaError(BusinessRuleError):
        pass

    class ZonaAlreadyExistsError(ConflictError):
        pass

    @staticmethod
    def _check_geom(geom: Polygon) -> None:
        if geom.srid is not None and geom.srid != SRID_WGS84:
            raise ZonaService.GeometriaInvalidaError(
                f"La geometría debe estar en SRID {SRID_WGS84}, llegó {geom.srid}",
                detail={"srid": geom.srid},
            )
        if geom.empty:
            raise ZonaService.GeometriaInvalidaError("La geometría está vacía")
        if not geom.valid:
            raise ZonaService.GeometriaInvalidaError(
                f"La geometría no es válida: {geom.valid_reason}",
                detail={"motivo": geom.valid_reason},
            )

    @staticmethod
    def get_covering_zones(punto: Point) -> list[Zona]:
        return list(Zona.objects.filter(geom__covers=punto))

    @staticmethod
    def get_zones_for_location(ubicacion: Ubicacion) -> list[Zona]:
        if ubicacion.coordinates is None:
            return []
        return ZonaService.get_covering_zones(ubicacion.coordinates)

    @staticmethod
    def get_zona(zona_id: int) -> Zona | None:
        return Zona.objects.filter(pk=zona_id).first()

    @staticmethod
    def create_zona(nombre: str, geom: Polygon) -> Zona:
        ZonaService._check_geom(geom)
        try:
            with transaction.atomic():
                return Zona.objects.create(nombre=nombre, geom=geom)
        except IntegrityError as exc:
            raise ZonaService.ZonaAlreadyExistsError(
                f"Ya existe una zona con nombre {nombre}",
                detail={"nombre": nombre},
            ) from exc

    @staticmethod
    def update_geom(zona: Zona, geom: Polygon) -> Zona:
        ZonaService._check_geom(geom)
        zona.geom = geom
        zona.save(update_fields=["geom", "updated_at"])
        return zona
