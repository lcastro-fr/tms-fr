from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from logistica.dtos import CostoOrdenServicioOut
from logistica.services import CostoOrdenServicioService, OrdenServicioService
from shared.exceptions import BusinessRuleError
from tracking.services import RemitoService, TicketService
from transportista.enums import TipoOperacion
from transportista.services import TarifarioService

logger = logging.getLogger(__name__)


class CalcularCostoOrdenServicioUseCase:
    """
    Costo de una orden de servicio: flete más adicional por día.
    """

    class FechaViajeRequeridaError(BusinessRuleError):
        pass

    class ConceptoCamaraRequeridoError(BusinessRuleError):
        pass

    class OrdenServicioNoFacturable(BusinessRuleError):
        pass

    @staticmethod
    @transaction.atomic
    def execute(orden_servicio_id: int) -> CostoOrdenServicioOut:
        orden = OrdenServicioService.get_orden_servicio_or_raise(orden_servicio_id)

        if orden.facturable is False:
            raise CalcularCostoOrdenServicioUseCase.OrdenServicioNoFacturable(
                f"La orden de servicio {orden.id} no es facturable",
                detail={"orden_servicio_id": orden.id},
            )

        if orden.fecha_viaje is None:
            raise CalcularCostoOrdenServicioUseCase.FechaViajeRequeridaError(
                f"La orden de servicio {orden.id} no tiene fecha_viaje",
                detail={"orden_servicio_id": orden.id},
            )

        tarifario = TarifarioService.get_tarifario_at(orden.transportista_id, orden.fecha_viaje)

        es_camara = orden.tipo_operacion == TipoOperacion.CAMARA.value
        if es_camara:
            tarifa_flete = None
            precio_flete = Decimal("0.00")
            modalidad = None
            destinos = []
        else:
            # Los explícitos se usan tal cual; sin ellos se derivan de los remitos.
            destinos = OrdenServicioService.list_destinos_ubicaciones(orden.id)
            if not destinos:
                crudos = RemitoService.get_distinct_destinos(orden.id)
                destinos = OrdenServicioService.resolve_destinos(orden, crudos)
            tarifa_flete = TarifarioService.resolve_tarifa_flete(
                tarifario, destinos, orden.tipo_camion, orden.hombreador
            )
            precio_flete = tarifa_flete.precio
            modalidad = tarifa_flete.modalidad

        dias = TicketService.get_dias_permanencia(orden.id)
        tarifa_concepto = TarifarioService.get_tarifa_concepto(tarifario, orden.tipo_operacion)

        if es_camara and tarifa_concepto is None:
            raise CalcularCostoOrdenServicioUseCase.ConceptoCamaraRequeridoError(
                f"El tarifario {tarifario.id} no tiene precio por día para cámara",
                detail={"tarifario_id": tarifario.id, "orden_servicio_id": orden.id},
            )

        costo = CostoOrdenServicioService.replace_costo(
            orden_servicio=orden,
            tarifa_flete=tarifa_flete,
            precio_flete=precio_flete,
            tarifa_concepto=tarifa_concepto,
            dias=dias,
            precio_dia=tarifa_concepto.precio if tarifa_concepto else None,
            tipo_operacion=orden.tipo_operacion,
            modalidad=modalidad,
            tipo_camion=orden.tipo_camion,
            hombreador=orden.hombreador,
            cantidad_destinos=len(destinos),
            fecha_viaje=orden.fecha_viaje,
        )

        logger.info(
            "Costo OS %s: flete=%s dias=%s tipo_operacion=%s",
            orden.id,
            precio_flete,
            dias,
            orden.tipo_operacion,
        )
        return CostoOrdenServicioOut.from_model(costo)
