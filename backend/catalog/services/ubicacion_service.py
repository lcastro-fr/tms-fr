from __future__ import annotations

from django.contrib.gis.geos import Point

from catalog.enums import SRID_WGS84, TipoUbicacion
from catalog.models import Ubicacion
from shared.exceptions import BusinessRuleError, NotFoundError


class UbicacionService:
    class UbicacionNotFoundError(NotFoundError):
        pass

    class CoordenadasInvalidasError(BusinessRuleError):
        pass

    class TipoInvalidoError(BusinessRuleError):
        pass

    @staticmethod
    def get_ubicacion_by_codigo(codigo: str) -> Ubicacion | None:
        return Ubicacion.objects.filter(codigo=codigo).first()

    @staticmethod
    def get_ubicacion_by_codigo_or_raise(codigo: str) -> Ubicacion:
        ubicacion = UbicacionService.get_ubicacion_by_codigo(codigo)
        if ubicacion is None:
            raise UbicacionService.UbicacionNotFoundError(
                f"No se encontró la ubicación con código {codigo}",
                detail={"codigo": codigo},
            )
        return ubicacion

    @staticmethod
    def _build_coordinates(lat: float | None, lng: float | None) -> Point | None:
        if lat is None and lng is None:
            return None
        if lat is None or lng is None:
            raise UbicacionService.CoordenadasInvalidasError(
                "Latitud y longitud son obligatorias",
                detail={"lat": lat, "lng": lng},
            )
        if not -90 <= lat <= 90:
            raise UbicacionService.CoordenadasInvalidasError(
                f"Latitud fuera de rango: {lat}", detail={"lat": lat}
            )
        if not -180 <= lng <= 180:
            raise UbicacionService.CoordenadasInvalidasError(
                f"Longitud fuera de rango: {lng}", detail={"lng": lng}
            )
        return Point(lng, lat, srid=SRID_WGS84)

    @staticmethod
    def _check_tipo(tipo: str) -> None:
        if tipo not in {t.value for t in TipoUbicacion}:
            raise UbicacionService.TipoInvalidoError(
                f"Tipo de ubicación desconocido: {tipo!r}",
                detail={"tipo": tipo},
            )

    @staticmethod
    def upsert_by_codigo(
        codigo: str,
        tipo: str,
        nombre: str,
        calle: str,
        localidad: str,
        provincia: str,
        pais: str = "Argentina",
        lat: float | None = None,
        lng: float | None = None,
    ) -> tuple[Ubicacion, bool]:
        """Devuelve (ubicacion, creada). Idempotente por codigo."""
        UbicacionService._check_tipo(tipo)
        coordinates = UbicacionService._build_coordinates(lat, lng)

        return Ubicacion.objects.update_or_create(
            codigo=codigo,
            defaults={
                "tipo": tipo,
                "nombre": nombre,
                "calle": calle,
                "localidad": localidad,
                "provincia": provincia,
                "pais": pais,
                "coordinates": coordinates,
            },
        )

    @staticmethod
    def resolve_codigos(codigos: list[str]) -> tuple[list[Ubicacion], list[str]]:
        encontradas = Ubicacion.objects.filter(codigo__in=codigos)
        por_codigo = {u.codigo: u for u in encontradas}
        faltantes = [c for c in codigos if c not in por_codigo]
        return [por_codigo[c] for c in codigos if c in por_codigo], faltantes
