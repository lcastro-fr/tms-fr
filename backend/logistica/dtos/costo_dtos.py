from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel

if TYPE_CHECKING:
    from logistica.models import CostoOrdenServicio


class CostoOrdenServicioOut(BaseModel):
    orden_servicio_id: int
    tipo_operacion: str

    tarifa_flete_id: int | None
    precio_flete: Decimal

    tarifa_concepto_id: int | None
    dias: int
    precio_dia: Decimal | None
    subtotal_adicional: Decimal

    total: Decimal

    modalidad: str | None
    tipo_camion: str | None
    hombreador: bool
    cantidad_destinos: int
    fecha_viaje: AwareDatetime
    calculado_at: AwareDatetime

    @classmethod
    def from_model(cls, costo: CostoOrdenServicio) -> CostoOrdenServicioOut:
        subtotal = Decimal("0.00") if costo.precio_dia is None else costo.dias * costo.precio_dia
        return cls(
            orden_servicio_id=costo.orden_servicio_id,
            tipo_operacion=costo.tipo_operacion,
            tarifa_flete_id=costo.tarifa_flete_id,
            precio_flete=costo.precio_flete,
            tarifa_concepto_id=costo.tarifa_concepto_id,
            dias=costo.dias,
            precio_dia=costo.precio_dia,
            subtotal_adicional=subtotal,
            total=costo.precio_flete + subtotal,
            modalidad=costo.modalidad,
            tipo_camion=costo.tipo_camion,
            hombreador=costo.hombreador,
            cantidad_destinos=costo.cantidad_destinos,
            fecha_viaje=costo.fecha_viaje,
            calculado_at=costo.created_at,
        )
