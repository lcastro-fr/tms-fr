from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q

from catalog.enums import PAIS_LOCAL
from catalog.models import Ubicacion
from catalog.services import UbicacionService
from logistica.enums import DESTINO_DEFAULT_POR_VIA
from logistica.models import OrdenServicio, OrdenServicioDestino
from shared.exceptions import BusinessRuleError, NotFoundError
from transportista.enums import TipoOperacion, Via


class OrdenServicioService:
    class OrdenServicioNotFoundError(NotFoundError):
        pass

    class DestinoSinPaisError(BusinessRuleError):
        pass

    class ViaSinDestinoDefaultError(BusinessRuleError):
        pass

    class DestinoDuplicadoError(BusinessRuleError):
        pass

    class DestinoInexistenteError(BusinessRuleError):
        pass

    @staticmethod
    def create_orden_servicio(
        origen_id: int,
        transportista_id: int,
        fecha_viaje: datetime | None = None,
        tipo_operacion: str = TipoOperacion.CARGA.value,
        tipo_camion: str | None = None,
        hombreador: bool = False,
        via: str = Via.TERRESTRE.value,
        facturable: bool = False,
    ) -> OrdenServicio:
        return OrdenServicio.objects.create(
            origen_id=origen_id,
            transportista_id=transportista_id,
            fecha_viaje=fecha_viaje,
            tipo_operacion=tipo_operacion,
            tipo_camion=tipo_camion,
            hombreador=hombreador,
            via=via,
            facturable=facturable,
        )

    @staticmethod
    def _inicio_del_dia(dia: date) -> datetime:
        return datetime.combine(dia, time.min, tzinfo=ZoneInfo(settings.TZ_OPERACION))

    @staticmethod
    def list_ordenes_servicio(
        facturable: bool | None = None,
        con_costo: bool | None = None,
        numero: str | None = None,
        fecha_viaje_desde: date | None = None,
        fecha_viaje_hasta: date | None = None,
        incluir_sin_fecha: bool | None = None,
    ) -> list[OrdenServicio]:
        qs = OrdenServicio.objects.select_related("origen", "transportista")
        if facturable is not None:
            qs = qs.filter(facturable=facturable)
        if con_costo is not None:
            tiene_costo = Q(costos__active=True)
            qs = qs.filter(tiene_costo) if con_costo else qs.exclude(tiene_costo)
        if numero:
            qs = qs.filter(
                Q(tickets__numero__icontains=numero, tickets__active=True)
                | Q(remitos__numero__icontains=numero, remitos__active=True)
            ).distinct()
        rango = Q()
        if fecha_viaje_desde is not None:
            rango &= Q(fecha_viaje__gte=OrdenServicioService._inicio_del_dia(fecha_viaje_desde))
        if fecha_viaje_hasta is not None:
            rango &= Q(
                fecha_viaje__lt=OrdenServicioService._inicio_del_dia(
                    fecha_viaje_hasta + timedelta(days=1)
                )
            )
        if rango:
            if incluir_sin_fecha:
                rango |= Q(fecha_viaje__isnull=True)
            qs = qs.filter(rango)
        return list(qs.order_by("-fecha_viaje", "-id"))

    @staticmethod
    def get_orden_servicio(orden_servicio_id: int) -> OrdenServicio | None:
        return (
            OrdenServicio.objects.select_related("origen", "transportista")
            .filter(pk=orden_servicio_id)
            .first()
        )

    @staticmethod
    def get_orden_servicio_or_raise(orden_servicio_id: int) -> OrdenServicio:
        orden_servicio = OrdenServicioService.get_orden_servicio(orden_servicio_id)
        if orden_servicio is None:
            raise OrdenServicioService.OrdenServicioNotFoundError(
                f"No existe la orden de servicio {orden_servicio_id}",
                detail={"orden_servicio_id": orden_servicio_id},
            )
        return orden_servicio

    @staticmethod
    def update_orden_servicio(
        orden_servicio: OrdenServicio,
        fecha_viaje: datetime | None,
        tipo_operacion: str,
        tipo_camion: str | None,
        via: str,
        hombreador: bool,
        facturable: bool,
    ) -> OrdenServicio:
        orden_servicio.fecha_viaje = fecha_viaje
        orden_servicio.tipo_operacion = tipo_operacion
        orden_servicio.tipo_camion = tipo_camion
        orden_servicio.via = via
        orden_servicio.hombreador = hombreador
        orden_servicio.facturable = facturable
        with transaction.atomic():
            orden_servicio.save(
                update_fields=[
                    "fecha_viaje",
                    "tipo_operacion",
                    "tipo_camion",
                    "via",
                    "hombreador",
                    "facturable",
                    "updated_at",
                ]
            )
        return orden_servicio

    @staticmethod
    def list_destinos(orden_servicio_id: int) -> list[OrdenServicioDestino]:
        return list(
            OrdenServicioDestino.objects.filter(orden_servicio_id=orden_servicio_id)
            .select_related("ubicacion", "ubicacion__pais")
            .order_by("secuencia", "id")
        )

    @staticmethod
    def list_destinos_ubicaciones(orden_servicio_id: int) -> list[Ubicacion]:
        return [d.ubicacion for d in OrdenServicioService.list_destinos(orden_servicio_id)]

    @staticmethod
    def _check_destinos(ubicacion_ids: list[int]) -> None:
        vistos: set[int] = set()
        for indice, ubicacion_id in enumerate(ubicacion_ids):
            if ubicacion_id in vistos:
                raise OrdenServicioService.DestinoDuplicadoError(
                    f"El destino de la fila #{indice + 1} está cargado más de una vez",
                    detail={"coleccion": "destinos", "indice": indice},
                )
            vistos.add(ubicacion_id)

        if not vistos:
            return
        existentes = set(Ubicacion.objects.filter(pk__in=vistos).values_list("pk", flat=True))
        faltantes = sorted(vistos - existentes)
        if faltantes:
            raise OrdenServicioService.DestinoInexistenteError(
                f"No existen estas ubicaciones: {faltantes}",
                detail={"campo": "ubicacion_id", "ids": faltantes},
            )

    @staticmethod
    def replace_destinos(orden_servicio: OrdenServicio, ubicacion_ids: list[int]) -> None:
        """
        Deja la OS exactamente con los destinos que llegan.
        """
        OrdenServicioService._check_destinos(ubicacion_ids)

        vigentes = [d.ubicacion_id for d in OrdenServicioService.list_destinos(orden_servicio.id)]
        if vigentes == ubicacion_ids:
            return

        try:
            with transaction.atomic():
                OrdenServicioDestino.objects.filter(orden_servicio=orden_servicio).delete()
                OrdenServicioDestino.objects.bulk_create(
                    [
                        OrdenServicioDestino(
                            orden_servicio=orden_servicio,
                            ubicacion_id=ubicacion_id,
                            secuencia=secuencia,
                        )
                        for secuencia, ubicacion_id in enumerate(ubicacion_ids)
                    ]
                )
        except IntegrityError as exc:
            raise OrdenServicioService.DestinoDuplicadoError(
                "Hay destinos repetidos en la orden de servicio",
                detail={"orden_servicio_id": orden_servicio.id},
            ) from exc

    @staticmethod
    def _etiqueta(ubicacion: Ubicacion) -> str:
        return ubicacion.codigo or f"id={ubicacion.id}"

    @staticmethod
    def resolve_destinos(orden: OrdenServicio, destinos: list[Ubicacion]) -> list[Ubicacion]:
        """
        Los destinos que se tarifan y se rutean.
        """
        sin_pais = [OrdenServicioService._etiqueta(d) for d in destinos if d.pais_id is None]
        if sin_pais:
            raise OrdenServicioService.DestinoSinPaisError(
                f"Destinos sin país, no se puede resolver el destino: {', '.join(sin_pais)}",
                detail={"motivo": "sin_pais", "codigos": sin_pais},
            )

        extranjeros = [d for d in destinos if d.pais_id != PAIS_LOCAL]
        if not extranjeros:
            return destinos

        clave = DESTINO_DEFAULT_POR_VIA.get(Via(orden.via))
        if clave is None:
            codigos = [OrdenServicioService._etiqueta(d) for d in extranjeros]
            raise OrdenServicioService.ViaSinDestinoDefaultError(
                f"La vía {orden.via} no tiene punto de salida definido para destinos "
                f"en el exterior: {', '.join(codigos)}",
                detail={"motivo": "via_sin_destino_default", "via": orden.via, "codigos": codigos},
            )

        salida = UbicacionService.get_ubicacion_by_destino_default_or_raise(clave)
        nacionales = [d for d in destinos if d.pais_id == PAIS_LOCAL]
        return list(dict.fromkeys([*nacionales, salida]))
