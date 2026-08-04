from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import transaction

from logistica.models import CostoOrdenServicio, OrdenServicio
from transportista.models import TarifaConceptoAdicional, TarifaFlete


class CostoOrdenServicioService:
    @staticmethod
    def get_costo_vigente(orden_servicio_id: int) -> CostoOrdenServicio | None:
        return CostoOrdenServicio.objects.filter(orden_servicio_id=orden_servicio_id).first()

    @staticmethod
    def replace_costo(
        orden_servicio: OrdenServicio,
        precio_flete: Decimal,
        dias: int,
        tipo_operacion: str,
        hombreador: bool,
        cantidad_destinos: int,
        fecha_viaje: datetime,
        tarifa_flete: TarifaFlete | None = None,
        tarifa_concepto: TarifaConceptoAdicional | None = None,
        precio_dia: Decimal | None = None,
        modalidad: str | None = None,
        tipo_camion: str | None = None,
    ) -> CostoOrdenServicio:
        with transaction.atomic():
            vigente = CostoOrdenServicioService.get_costo_vigente(orden_servicio.id)
            if vigente is not None:
                vigente.delete()

            return CostoOrdenServicio.objects.create(
                orden_servicio=orden_servicio,
                tarifa_flete=tarifa_flete,
                precio_flete=precio_flete,
                tarifa_concepto=tarifa_concepto,
                dias=dias,
                precio_dia=precio_dia,
                tipo_operacion=tipo_operacion,
                modalidad=modalidad,
                tipo_camion=tipo_camion,
                hombreador=hombreador,
                cantidad_destinos=cantidad_destinos,
                fecha_viaje=fecha_viaje,
            )
