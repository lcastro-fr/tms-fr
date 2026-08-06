from __future__ import annotations

from datetime import datetime

from catalog.enums import PAIS_LOCAL
from catalog.models import Ubicacion
from catalog.services import UbicacionService
from logistica.enums import DESTINO_DEFAULT_POR_VIA
from logistica.models import OrdenServicio
from shared.exceptions import BusinessRuleError, NotFoundError
from transportista.enums import TipoOperacion, Via


class OrdenServicioService:
    class OrdenServicioNotFoundError(NotFoundError):
        pass

    class DestinoSinPaisError(BusinessRuleError):
        pass

    class ViaSinDestinoDefaultError(BusinessRuleError):
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
    ) -> OrdenServicio:
        return OrdenServicio.objects.create(
            origen_id=origen_id,
            transportista_id=transportista_id,
            fecha_viaje=fecha_viaje,
            tipo_operacion=tipo_operacion,
            tipo_camion=tipo_camion,
            hombreador=hombreador,
            via=via,
        )

    @staticmethod
    def get_orden_servicio(orden_servicio_id: int) -> OrdenServicio | None:
        return OrdenServicio.objects.filter(pk=orden_servicio_id).first()

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
