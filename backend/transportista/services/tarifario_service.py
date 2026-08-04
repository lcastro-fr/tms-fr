from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.db.models import Q

from catalog.models import Ubicacion
from catalog.services import ZonaService
from shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from transportista.enums import ModalidadFlete
from transportista.models import TarifaFlete, Tarifario, Transportista


class TarifarioService:
    class TransportistaNotFoundError(NotFoundError):
        pass

    class TarifarioNotFoundError(NotFoundError):
        pass

    class VigenciaInvalidaError(BusinessRuleError):
        pass

    class TarifarioSolapadoError(ConflictError):
        pass

    class TarifarioAmbiguoError(ConflictError):
        pass

    class SinDestinosError(BusinessRuleError):
        pass

    class TipoCamionRequeridoError(BusinessRuleError):
        pass

    class TarifaNoResueltaError(BusinessRuleError):
        pass

    class TarifaAmbiguaError(ConflictError):
        pass

    @staticmethod
    def _check_aware(momento: datetime, campo: str) -> None:
        if momento.tzinfo is None:
            raise ValueError(f"{campo} debe ser tz-aware, llegó naive: {momento!r}")

    @staticmethod
    def _check_vigencia(vigente_desde: datetime, vigente_hasta: datetime | None) -> None:
        TarifarioService._check_aware(vigente_desde, "vigente_desde")
        if vigente_hasta is None:
            return
        TarifarioService._check_aware(vigente_hasta, "vigente_hasta")
        if vigente_hasta < vigente_desde:
            raise TarifarioService.VigenciaInvalidaError(
                f"vigente_hasta ({vigente_hasta}) es anterior a vigente_desde ({vigente_desde})",
                detail={
                    "vigente_desde": vigente_desde.isoformat(),
                    "vigente_hasta": vigente_hasta.isoformat(),
                },
            )

    @staticmethod
    def _check_solapamiento(
        transportista_id: int,
        vigente_desde: datetime,
        vigente_hasta: datetime | None,
        excluir_id: int | None = None,
    ) -> None:
        qs = Tarifario.objects.filter(transportista_id=transportista_id).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=vigente_desde)
        )
        if vigente_hasta is not None:
            qs = qs.filter(vigente_desde__lte=vigente_hasta)
        if excluir_id is not None:
            qs = qs.exclude(pk=excluir_id)

        conflicto = qs.first()
        if conflicto is not None:
            raise TarifarioService.TarifarioSolapadoError(
                f"La vigencia se solapa con el tarifario {conflicto.id} "
                f"({conflicto.vigente_desde} - {conflicto.vigente_hasta or 'sin cierre'})",
                detail={
                    "tarifario_id": conflicto.id,
                    "vigente_desde": conflicto.vigente_desde.isoformat(),
                    "vigente_hasta": (
                        conflicto.vigente_hasta.isoformat() if conflicto.vigente_hasta else None
                    ),
                },
            )

    @staticmethod
    def _lock_transportista(transportista_id: int) -> None:
        existe = Transportista.all_objects.select_for_update().filter(pk=transportista_id).exists()
        if not existe:
            raise TarifarioService.TransportistaNotFoundError(
                f"No existe el transportista {transportista_id}",
                detail={"transportista_id": transportista_id},
            )

    @staticmethod
    def create_tarifario(
        transportista_id: int,
        vigente_desde: datetime,
        vigente_hasta: datetime | None = None,
    ) -> Tarifario:
        TarifarioService._check_vigencia(vigente_desde, vigente_hasta)

        with transaction.atomic():
            TarifarioService._lock_transportista(transportista_id)
            TarifarioService._check_solapamiento(transportista_id, vigente_desde, vigente_hasta)
            return Tarifario.objects.create(
                transportista_id=transportista_id,
                vigente_desde=vigente_desde,
                vigente_hasta=vigente_hasta,
            )

    @staticmethod
    def cerrar_tarifario(tarifario: Tarifario, vigente_hasta: datetime) -> Tarifario:
        TarifarioService._check_vigencia(tarifario.vigente_desde, vigente_hasta)

        with transaction.atomic():
            TarifarioService._lock_transportista(tarifario.transportista_id)
            TarifarioService._check_solapamiento(
                tarifario.transportista_id,
                tarifario.vigente_desde,
                vigente_hasta,
                excluir_id=tarifario.id,
            )
            tarifario.vigente_hasta = vigente_hasta
            tarifario.save(update_fields=["vigente_hasta", "updated_at"])
            return tarifario

    @staticmethod
    def get_tarifario_at(transportista_id: int, momento: datetime) -> Tarifario:
        """
        Tarifario vigente en un momento dado.
        """
        TarifarioService._check_aware(momento, "momento")

        qs = Tarifario.objects.filter(
            transportista_id=transportista_id, vigente_desde__lte=momento
        ).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=momento))

        encontrados = list(qs[:2])
        if not encontrados:
            raise TarifarioService.TarifarioNotFoundError(
                f"El transportista {transportista_id} no tiene tarifario vigente "
                f"en {momento.isoformat()}",
                detail={
                    "transportista_id": transportista_id,
                    "momento": momento.isoformat(),
                },
            )
        if len(encontrados) > 1:
            raise TarifarioService.TarifarioAmbiguoError(
                f"El transportista {transportista_id} tiene {len(encontrados)}+ tarifarios "
                f"vigentes en {momento.isoformat()}: {[t.id for t in encontrados]}",
                detail={
                    "transportista_id": transportista_id,
                    "momento": momento.isoformat(),
                    "tarifarios": [t.id for t in encontrados],
                },
            )
        return encontrados[0]

    @staticmethod
    def resolve_tarifa_flete(
        tarifario: Tarifario,
        ubicaciones: list[Ubicacion],
        tipo_camion: str | None,
        hombreador: bool,
    ) -> TarifaFlete:
        """
        La única tarifa que corresponde a un viaje.

        Con un solo destino se intenta primero la tarifa por ubicación puntual y
        se cae a la zona. Con varios destinos se resuelve sólo por zona, y la
        zona tiene que cubrirlos a todos: un viaje no cruza zonas.
        """
        if not ubicaciones:
            raise TarifarioService.SinDestinosError(
                "No hay destinos para resolver la tarifa",
                detail={"tarifario_id": tarifario.id},
            )
        if not tipo_camion:
            raise TarifarioService.TipoCamionRequeridoError(
                "La orden de servicio no tiene tipo de camión, sin eso no hay tarifa",
                detail={"tarifario_id": tarifario.id},
            )

        modalidad = ModalidadFlete.para_destinos(len(ubicaciones))
        clave = {
            "tarifario": tarifario,
            "modalidad": modalidad.value,
            "tipo_camion": tipo_camion,
            "hombreador": hombreador,
        }

        if modalidad is ModalidadFlete.DIRECTO:
            tarifa = TarifaFlete.objects.filter(**clave, ubicacion=ubicaciones[0]).first()
            if tarifa is not None:
                return tarifa

        return TarifarioService._resolve_por_zona(clave, ubicaciones, modalidad)

    @staticmethod
    def _resolve_por_zona(
        clave: dict,
        ubicaciones: list[Ubicacion],
        modalidad: ModalidadFlete,
    ) -> TarifaFlete:
        sin_coordenadas = [u for u in ubicaciones if u.coordinates is None]
        if sin_coordenadas:
            codigos = [u.codigo for u in sin_coordenadas]
            raise TarifarioService.TarifaNoResueltaError(
                f"Destinos sin coordenadas, no se puede resolver la zona: {', '.join(codigos)}",
                detail={"motivo": "sin_coordenadas", "codigos": codigos},
            )

        zonas = ZonaService.get_zones_covering_all([u.coordinates for u in ubicaciones])
        if not zonas:
            codigos = [u.codigo for u in ubicaciones]
            raise TarifarioService.TarifaNoResueltaError(
                f"Ninguna zona cubre todos los destinos: {', '.join(codigos)}",
                detail={"motivo": "sin_zona_comun", "codigos": codigos},
            )

        tarifas = list(
            TarifaFlete.objects.filter(**clave, zona__in=zonas).select_related("zona")[:2]
        )
        if not tarifas:
            raise TarifarioService.TarifaNoResueltaError(
                f"El tarifario {clave['tarifario'].id} no tiene tarifa para "
                f"({modalidad.value}, {clave['tipo_camion']}, hombreador={clave['hombreador']}) "
                f"en las zonas {[z.nombre for z in zonas]}",
                detail={
                    "motivo": "sin_tarifa",
                    "modalidad": modalidad.value,
                    "tipo_camion": clave["tipo_camion"],
                    "hombreador": clave["hombreador"],
                    "zonas": [z.nombre for z in zonas],
                },
            )
        if len(tarifas) > 1:
            nombres = [t.zona.nombre for t in tarifas]
            raise TarifarioService.TarifaAmbiguaError(
                f"El tarifario {clave['tarifario'].id} tiene tarifas en más de una zona que "
                f"cubre los destinos: {', '.join(nombres)}",
                detail={"tarifario_id": clave["tarifario"].id, "zonas": nombres},
            )
        return tarifas[0]
