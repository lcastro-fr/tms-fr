from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.db.models import Q

from catalog.enums import SRID_WGS84, DestinoDefault, TipoUbicacion
from catalog.models import Pais, Ubicacion
from shared.exceptions import BusinessRuleError, ConflictError, NotFoundError


class UbicacionService:
    class UbicacionNotFoundError(NotFoundError):
        pass

    class CoordenadasInvalidasError(BusinessRuleError):
        pass

    class TipoInvalidoError(BusinessRuleError):
        pass

    class DestinoDefaultNotFoundError(NotFoundError):
        pass

    class UbicacionAlreadyExistsError(ConflictError):
        pass

    @staticmethod
    def list_ubicaciones(
        validada: bool | None = None, con_coordenadas: bool | None = None
    ) -> list[Ubicacion]:
        qs = Ubicacion.objects.select_related("pais")
        if validada is not None:
            qs = qs.filter(validada=validada)
        if con_coordenadas is not None:
            qs = qs.filter(coordinates__isnull=not con_coordenadas)
        return list(qs.order_by("nombre"))

    @staticmethod
    def list_ubicaciones_para_opciones() -> list[Ubicacion]:
        """Sin dirección y con `tiene_coordenadas` anotado para no traer la geometría."""
        return list(
            Ubicacion.objects.only(
                "id", "codigo", "nombre", "tipo", "localidad", "provincia", "pais"
            )
            .select_related("pais")
            .annotate(tiene_coordenadas=Q(coordinates__isnull=False))
            .order_by("nombre")
        )

    @staticmethod
    def get_ubicacion(ubicacion_id: int) -> Ubicacion | None:
        return Ubicacion.objects.filter(pk=ubicacion_id).first()

    @staticmethod
    def get_ubicacion_or_raise(ubicacion_id: int) -> Ubicacion:
        ubicacion = UbicacionService.get_ubicacion(ubicacion_id)
        if ubicacion is None:
            raise UbicacionService.UbicacionNotFoundError(
                f"No existe la ubicación {ubicacion_id}",
                detail={"ubicacion_id": ubicacion_id},
            )
        return ubicacion

    @staticmethod
    def create_ubicacion(
        nombre: str,
        tipo: str,
        calle: str,
        localidad: str,
        provincia: str,
        pais: Pais,
        lat: float,
        lng: float,
        codigo: str | None = None,
    ) -> Ubicacion:
        """Nace validada: el alta exige coordenada y el humano ya la vio."""
        UbicacionService._check_tipo(tipo)
        coordinates = UbicacionService._build_coordinates(lat, lng)

        try:
            with transaction.atomic():
                return Ubicacion.objects.create(
                    codigo=codigo,
                    tipo=tipo,
                    nombre=nombre,
                    calle=calle,
                    localidad=localidad,
                    provincia=provincia,
                    pais=pais,
                    coordinates=coordinates,
                    validada=True,
                )
        except IntegrityError as exc:
            if codigo is None:
                raise
            raise UbicacionService.UbicacionAlreadyExistsError(
                f"Ya existe una ubicación con código {codigo}",
                detail={"codigo": codigo},
            ) from exc

    @staticmethod
    def update_ubicacion(
        ubicacion: Ubicacion, nombre: str, tipo: str, localidad: str | None , provincia: str | None, calle: str | None, lat: float, lng: float
    ) -> Ubicacion:
        UbicacionService._check_tipo(tipo)
        coordinates = UbicacionService._build_coordinates(lat, lng)

        ubicacion.nombre = nombre
        ubicacion.tipo = tipo
        ubicacion.coordinates = coordinates

        if provincia is not None:
            ubicacion.provincia = provincia

        if localidad is not None:
            ubicacion.localidad = localidad

        if calle is not None:
            ubicacion.calle = calle

        ubicacion.validada = True
        with transaction.atomic():
            ubicacion.save(
                update_fields=["nombre", "tipo", "coordinates", "localidad", "provincia", "calle", "validada", "updated_at"]
            )
        return ubicacion

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
    def get_ubicacion_by_destino_default(clave: DestinoDefault) -> Ubicacion | None:
        return Ubicacion.objects.filter(destino_default=clave.value).first()

    @staticmethod
    def get_ubicacion_by_destino_default_or_raise(clave: DestinoDefault) -> Ubicacion:
        ubicacion = UbicacionService.get_ubicacion_by_destino_default(clave)
        if ubicacion is None:
            raise UbicacionService.DestinoDefaultNotFoundError(
                f"Ninguna ubicación está marcada como destino por defecto {clave.value!r}",
                detail={"destino_default": clave.value},
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
        calle: str | None,
        localidad: str | None,
        provincia: str | None,
        pais: Pais | None = None,
        lat: float | None = None,
        lng: float | None = None,
        validada: bool = True,
    ) -> tuple[Ubicacion, bool]:
        """Devuelve (ubicacion, creada). Idempotente por codigo."""
        UbicacionService._check_tipo(tipo)
        coordinates = UbicacionService._build_coordinates(lat, lng)

        campos: dict[str, Any] = {
            "tipo": tipo,
            "nombre": nombre,
            "calle": calle or "",
            "localidad": localidad or "",
            "provincia": provincia or "",
        }
        al_crear = {**campos, "pais": pais, "coordinates": coordinates, "validada": validada}

        # Igual que coordinates: una fuente que no trae el dato no pisa el que ya está.
        if pais is not None:
            campos["pais"] = pais
        if coordinates is not None:
            campos["coordinates"] = coordinates

        return Ubicacion.objects.update_or_create(
            codigo=codigo, defaults=campos, create_defaults=al_crear
        )

    @staticmethod
    def resolve_codigos(codigos: list[str]) -> tuple[list[Ubicacion], list[str]]:
        encontradas = Ubicacion.objects.filter(codigo__in=codigos)
        por_codigo = {u.codigo: u for u in encontradas}
        faltantes = [c for c in codigos if c not in por_codigo]
        return [por_codigo[c] for c in codigos if c in por_codigo], faltantes
