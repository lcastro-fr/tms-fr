from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from catalog.models import Ubicacion, Zona
from catalog.services import ZonaService
from shared.exceptions import BusinessRuleError, ConflictError, NotFoundError
from transportista.enums import ConceptoUnidadMedida, ModalidadFlete
from transportista.models import (
    ConceptoAdicional,
    TarifaConceptoAdicional,
    TarifaFlete,
    Tarifario,
    Transportista,
)


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

    class UnidadConceptoInvalidaError(BusinessRuleError):
        pass

    class TarifarioEnUsoError(ConflictError):
        pass

    class TarifaCongeladaError(ConflictError):
        pass

    class TarifaDuplicadaError(ConflictError):
        pass

    class AlcanceTarifaInvalidoError(BusinessRuleError):
        pass

    class ReferenciaInvalidaError(BusinessRuleError):
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
    def update_tarifario(
        tarifario: Tarifario,
        transportista_id: int,
        vigente_desde: datetime,
        vigente_hasta: datetime | None,
    ) -> Tarifario:
        TarifarioService._check_vigencia(vigente_desde, vigente_hasta)

        with transaction.atomic():
            TarifarioService._lock_transportista(transportista_id)
            TarifarioService._check_solapamiento(
                transportista_id, vigente_desde, vigente_hasta, excluir_id=tarifario.id
            )
            tarifario.transportista_id = transportista_id
            tarifario.vigente_desde = vigente_desde
            tarifario.vigente_hasta = vigente_hasta
            tarifario.save(
                update_fields=["transportista", "vigente_desde", "vigente_hasta", "updated_at"]
            )
            return tarifario

    @staticmethod
    def delete_tarifario(tarifario: Tarifario) -> None:
        try:
            with transaction.atomic():
                tarifario.delete()
        except ProtectedError as exc:
            raise TarifarioService.TarifarioEnUsoError(
                "El tarifario tiene tarifas usadas para costear una orden de servicio",
                detail={"tarifario_id": tarifario.id, "costos": len(exc.protected_objects)},
            ) from exc

    @staticmethod
    def list_tarifarios(
        transportista_id: int | None = None, vencidos: bool | None = None
    ) -> list[Tarifario]:
        """
        El filtro es por vencimiento y no por vigencia a propósito: un tarifario cargado
        con fecha futura todavía no rige, pero tampoco es historia, y esconderlo haría
        desaparecer de la pantalla el que el usuario acaba de dar de alta.
        """
        qs = Tarifario.objects.select_related("transportista")
        if transportista_id is not None:
            qs = qs.filter(transportista_id=transportista_id)
        if vencidos is not None:
            vencido = Q(vigente_hasta__isnull=False) & Q(vigente_hasta__lt=timezone.now())
            qs = qs.filter(vencido) if vencidos else qs.exclude(vencido)
        return list(qs.order_by("transportista__razon_social", "-vigente_desde"))

    @staticmethod
    def get_tarifario(tarifario_id: int) -> Tarifario | None:
        return Tarifario.objects.select_related("transportista").filter(pk=tarifario_id).first()

    @staticmethod
    def get_tarifario_or_raise(tarifario_id: int) -> Tarifario:
        tarifario = TarifarioService.get_tarifario(tarifario_id)
        if tarifario is None:
            raise TarifarioService.TarifarioNotFoundError(
                f"No existe el tarifario {tarifario_id}",
                detail={"tarifario_id": tarifario_id},
            )
        return tarifario

    @staticmethod
    def get_hijos(
        tarifario_id: int,
    ) -> tuple[list[TarifaFlete], list[TarifaConceptoAdicional]]:
        fletes = (
            TarifaFlete.objects.filter(tarifario_id=tarifario_id)
            .select_related("zona", "ubicacion")
            .order_by(
                "modalidad", "tipo_camion", "hombreador", "zona__nombre", "ubicacion__nombre", "id"
            )
        )
        conceptos = (
            TarifaConceptoAdicional.objects.filter(tarifario_id=tarifario_id)
            .select_related("concepto")
            .order_by("concepto__codigo")
        )
        return list(fletes), list(conceptos)

    @staticmethod
    def tarifarios_en_uso(tarifario_ids: list[int]) -> set[int]:
        """
        Los que tienen al menos una tarifa referenciada por un costo vigente.
        """
        if not tarifario_ids:
            return set()

        fletes = TarifaFlete.all_objects.filter(
            tarifario_id__in=tarifario_ids, costos__active=True
        ).values_list("tarifario_id", flat=True)
        conceptos = TarifaConceptoAdicional.all_objects.filter(
            tarifario_id__in=tarifario_ids, costos__active=True
        ).values_list("tarifario_id", flat=True)
        return set(fletes) | set(conceptos)

    @staticmethod
    def esta_en_uso(tarifario_id: int) -> bool:
        return tarifario_id in TarifarioService.tarifarios_en_uso([tarifario_id])

    @staticmethod
    def contar_tarifas(tarifario_ids: list[int]) -> dict[int, tuple[int, int]]:
        """Por tarifario, (tarifas de flete, tarifas de concepto) vigentes."""
        if not tarifario_ids:
            return {}

        fletes = Counter(
            TarifaFlete.objects.filter(tarifario_id__in=tarifario_ids).values_list(
                "tarifario_id", flat=True
            )
        )
        conceptos = Counter(
            TarifaConceptoAdicional.objects.filter(tarifario_id__in=tarifario_ids).values_list(
                "tarifario_id", flat=True
            )
        )
        return {tid: (fletes[tid], conceptos[tid]) for tid in tarifario_ids}

    @staticmethod
    def _check_alcance(fletes: list[dict]) -> None:
        for indice, fila in enumerate(fletes):
            if bool(fila.get("zona_id")) == bool(fila.get("ubicacion_id")):
                raise TarifarioService.AlcanceTarifaInvalidoError(
                    f"La tarifa de flete #{indice + 1} tiene que apuntar a una zona o a una "
                    f"ubicación, nunca a las dos ni a ninguna",
                    detail={"indice": indice},
                )

    @staticmethod
    def _clave_flete_dict(fila: dict) -> tuple:
        return (
            fila.get("zona_id"),
            fila.get("ubicacion_id"),
            fila["modalidad"],
            fila["tipo_camion"],
            fila["hombreador"],
        )

    @staticmethod
    def _clave_flete_model(flete: TarifaFlete) -> tuple:
        return (
            flete.zona_id,
            flete.ubicacion_id,
            flete.modalidad,
            flete.tipo_camion,
            flete.hombreador,
        )

    @staticmethod
    def _check_duplicados(fletes: list[dict], conceptos: list[dict]) -> None:
        vistas: set[tuple] = set()
        for indice, fila in enumerate(fletes):
            clave = TarifarioService._clave_flete_dict(fila)
            if clave in vistas:
                raise TarifarioService.TarifaDuplicadaError(
                    f"La tarifa de flete #{indice + 1} repite una clave ya cargada "
                    f"(alcance, modalidad, tipo de camión y hombreador)",
                    detail={"coleccion": "tarifas_flete", "indice": indice},
                )
            vistas.add(clave)

        conceptos_vistos: set[int] = set()
        for indice, fila in enumerate(conceptos):
            if fila["concepto_id"] in conceptos_vistos:
                raise TarifarioService.TarifaDuplicadaError(
                    f"El concepto de la fila #{indice + 1} está cargado más de una vez",
                    detail={"coleccion": "tarifas_concepto", "indice": indice},
                )
            conceptos_vistos.add(fila["concepto_id"])

    @staticmethod
    def _check_existen(campo: str, pedidos: set[int], existentes: set[int]) -> None:
        faltantes = sorted(pedidos - existentes)
        if faltantes:
            raise TarifarioService.ReferenciaInvalidaError(
                f"No existen estos {campo}: {faltantes}",
                detail={"campo": campo, "ids": faltantes},
            )

    @staticmethod
    def _check_referencias(fletes: list[dict], conceptos: list[dict]) -> None:
        """
        Un id inexistente tiene que ser 422 y no el IntegrityError de la FK, que sería 500.
        """
        zonas = {f["zona_id"] for f in fletes if f.get("zona_id")}
        if zonas:
            TarifarioService._check_existen(
                "zona_id",
                zonas,
                set(Zona.objects.filter(pk__in=zonas).values_list("pk", flat=True)),
            )

        ubicaciones = {f["ubicacion_id"] for f in fletes if f.get("ubicacion_id")}
        if ubicaciones:
            TarifarioService._check_existen(
                "ubicacion_id",
                ubicaciones,
                set(Ubicacion.objects.filter(pk__in=ubicaciones).values_list("pk", flat=True)),
            )

        conceptos_ids = {c["concepto_id"] for c in conceptos}
        if conceptos_ids:
            TarifarioService._check_existen(
                "concepto_id",
                conceptos_ids,
                set(
                    ConceptoAdicional.objects.filter(pk__in=conceptos_ids).values_list(
                        "pk", flat=True
                    )
                ),
            )

    @staticmethod
    def replace_hijos(tarifario: Tarifario, fletes: list[dict], conceptos: list[dict]) -> None:
        """
        Deja el tarifario exactamente con las filas que llegan.
        """
        TarifarioService._check_alcance(fletes)
        TarifarioService._check_duplicados(fletes, conceptos)
        TarifarioService._check_referencias(fletes, conceptos)

        try:
            with transaction.atomic():
                TarifaFlete.objects.filter(tarifario=tarifario).delete()
                TarifaConceptoAdicional.objects.filter(tarifario=tarifario).delete()
                TarifaFlete.objects.bulk_create(
                    [TarifaFlete(tarifario=tarifario, **fila) for fila in fletes]
                )
                TarifaConceptoAdicional.objects.bulk_create(
                    [TarifaConceptoAdicional(tarifario=tarifario, **fila) for fila in conceptos]
                )
        except ProtectedError as exc:
            raise TarifarioService.TarifarioEnUsoError(
                "El tarifario tiene tarifas usadas para costear una orden de servicio",
                detail={"tarifario_id": tarifario.id, "costos": len(exc.protected_objects)},
            ) from exc
        except IntegrityError as exc:
            raise TarifarioService.TarifaDuplicadaError(
                "Hay tarifas repetidas en el tarifario",
                detail={"tarifario_id": tarifario.id},
            ) from exc

    @staticmethod
    def agregar_hijos(tarifario: Tarifario, fletes: list[dict], conceptos: list[dict]) -> None:
        """
        Suma filas a un tarifario en uso. Las vigentes están congeladas por un costo: no se
        pueden modificar ni quitar, sólo se crean las de clave nueva.
        """
        TarifarioService._check_alcance(fletes)
        TarifarioService._check_duplicados(fletes, conceptos)
        TarifarioService._check_referencias(fletes, conceptos)

        fletes_actuales = {
            TarifarioService._clave_flete_model(f): f
            for f in TarifaFlete.objects.filter(tarifario=tarifario)
        }
        conceptos_actuales = {
            c.concepto_id: c
            for c in TarifaConceptoAdicional.objects.filter(tarifario=tarifario)
        }

        nuevos_flete = TarifarioService._solo_nuevos(
            "tarifas_flete",
            fletes,
            fletes_actuales,
            TarifarioService._clave_flete_dict,
        )
        nuevos_concepto = TarifarioService._solo_nuevos(
            "tarifas_concepto",
            conceptos,
            conceptos_actuales,
            lambda fila: fila["concepto_id"],
        )

        with transaction.atomic():
            TarifaFlete.objects.bulk_create(
                [TarifaFlete(tarifario=tarifario, **fila) for fila in nuevos_flete]
            )
            TarifaConceptoAdicional.objects.bulk_create(
                [TarifaConceptoAdicional(tarifario=tarifario, **fila) for fila in nuevos_concepto]
            )

    @staticmethod
    def _solo_nuevos(
        coleccion: str,
        filas: list[dict],
        actuales: dict,
        clave_de: Callable[[dict], object],
    ) -> list[dict]:
        """
        Filas de clave nueva a crear; rechaza modificar o quitar una fila congelada.
        """
        nuevos: list[dict] = []
        vistas: set = set()
        for indice, fila in enumerate(filas):
            clave = clave_de(fila)
            vistas.add(clave)
            existente = actuales.get(clave)
            if existente is None:
                nuevos.append(fila)
            elif existente.precio != fila["precio"]:
                raise TarifarioService.TarifaCongeladaError(
                    f"No se puede modificar el precio de una tarifa ya usada para costear "
                    f"({coleccion} #{indice + 1}): cerrá la vigencia y duplicá el tarifario",
                    detail={"coleccion": coleccion, "indice": indice, "motivo": "congelada"},
                )

        quitadas = set(actuales) - vistas
        if quitadas:
            raise TarifarioService.TarifaCongeladaError(
                f"No se puede quitar una tarifa ya usada para costear ({coleccion}): "
                f"cerrá la vigencia y duplicá el tarifario",
                detail={"coleccion": coleccion, "motivo": "quitada"},
            )
        return nuevos

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

    @staticmethod
    def get_tarifa_concepto(
        tarifario: Tarifario, tipo_operacion: str
    ) -> TarifaConceptoAdicional | None:
        """
        Precio por día del concepto que corresponde a un tipo de operación.
        """
        tarifa = (
            TarifaConceptoAdicional.objects.filter(
                tarifario=tarifario, concepto__tipo_operacion=tipo_operacion
            )
            .select_related("concepto")
            .first()
        )
        if tarifa is None:
            return None

        if tarifa.concepto.unidad != ConceptoUnidadMedida.DIA.value:
            raise TarifarioService.UnidadConceptoInvalidaError(
                f"El concepto {tarifa.concepto.codigo} está en {tarifa.concepto.unidad}, "
                f"y el cálculo de estadía es por día",
                detail={
                    "concepto": tarifa.concepto.codigo,
                    "unidad": tarifa.concepto.unidad,
                },
            )
        return tarifa
