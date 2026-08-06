from __future__ import annotations

import json

from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry, MultiPoint, Point, Polygon
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from catalog.enums import SRID_WGS84
from catalog.models import Ubicacion, Zona
from shared.exceptions import BusinessRuleError, ConflictError, NotFoundError


class ZonaService:
    class ZonaNotFoundError(NotFoundError):
        pass

    class GeometriaInvalidaError(BusinessRuleError):
        pass

    class ZonaAlreadyExistsError(ConflictError):
        pass

    class ZonaEnUsoError(ConflictError):
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
    def _build_polygon(coordinates: list) -> Polygon:
        try:
            geom = GEOSGeometry(json.dumps({"type": "Polygon", "coordinates": coordinates}))
        except (GDALException, GEOSException, ValueError, TypeError) as exc:
            raise ZonaService.GeometriaInvalidaError(
                f"No se pudo interpretar la geometría: {exc}",
                detail={"error": str(exc)},
            ) from exc

        if geom.geom_type != "Polygon":
            raise ZonaService.GeometriaInvalidaError(
                f"La geometría debe ser un Polygon, llegó {geom.geom_type}",
                detail={"geom_type": geom.geom_type},
            )

        ZonaService._check_geom(geom)
        return geom

    @staticmethod
    def get_covering_zones(punto: Point) -> list[Zona]:
        return list(Zona.objects.filter(geom__covers=punto))

    @staticmethod
    def get_zones_for_location(ubicacion: Ubicacion) -> list[Zona]:
        if ubicacion.coordinates is None:
            return []
        return ZonaService.get_covering_zones(ubicacion.coordinates)

    @staticmethod
    def get_zones_covering_all(puntos: list[Point]) -> list[Zona]:
        """
        Zonas que cubren TODOS los puntos.
        """
        if not puntos:
            return []
        objetivo = MultiPoint(*puntos, srid=SRID_WGS84)
        return list(Zona.objects.filter(geom__covers=objetivo))

    @staticmethod
    def list_zonas() -> list[Zona]:
        return list(Zona.objects.all())

    @staticmethod
    def get_zona(zona_id: int) -> Zona | None:
        return Zona.objects.filter(pk=zona_id).first()

    @staticmethod
    def get_zona_or_raise(zona_id: int) -> Zona:
        zona = ZonaService.get_zona(zona_id)
        if zona is None:
            raise ZonaService.ZonaNotFoundError(
                f"No existe la zona {zona_id}",
                detail={"zona_id": zona_id},
            )
        return zona

    @staticmethod
    def create_zona(nombre: str, coordinates: list) -> Zona:
        geom = ZonaService._build_polygon(coordinates)
        try:
            with transaction.atomic():
                return Zona.objects.create(nombre=nombre, geom=geom)
        except IntegrityError as exc:
            raise ZonaService.ZonaAlreadyExistsError(
                f"Ya existe una zona con nombre {nombre}",
                detail={"nombre": nombre},
            ) from exc

    @staticmethod
    def update_zona(zona: Zona, nombre: str, coordinates: list) -> Zona:
        geom = ZonaService._build_polygon(coordinates)
        zona.nombre = nombre
        zona.geom = geom
        try:
            with transaction.atomic():
                zona.save(update_fields=["nombre", "geom", "updated_at"])
        except IntegrityError as exc:
            raise ZonaService.ZonaAlreadyExistsError(
                f"Ya existe otra zona con nombre {nombre}",
                detail={"nombre": nombre},
            ) from exc
        return zona

    @staticmethod
    def delete_zona(zona: Zona) -> None:
        try:
            with transaction.atomic():
                zona.delete()
        except ProtectedError as exc:
            raise ZonaService.ZonaEnUsoError(
                f"La zona {zona.nombre} tiene tarifas de flete asociadas",
                detail={"nombre": zona.nombre, "tarifas_flete": len(exc.protected_objects)},
            ) from exc
