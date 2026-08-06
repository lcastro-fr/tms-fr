from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from core.auth import IngestApiKeyAuth
from logistica.dtos import CostoOrdenServicioOut
from routing.factory import build_geocoder
from shared.dtos import ERRORS
from tracking.dtos import TicketIngestIn, TicketIngestOut
from tracking.use_cases import CalcularCostoOrdenServicioUseCase, IngestTicketUseCase

router = Router(tags=["tickets"])
ordenes_router = Router(tags=["ordenes de servicio"])


@router.post(
    "/ingest",
    response={201: TicketIngestOut, **ERRORS},
    auth=IngestApiKeyAuth(),
    summary="Ingesta de un ticket",
    operation_id="ingestTicket",
)
def ingest_ticket(request: HttpRequest, payload: TicketIngestIn):
    return 201, IngestTicketUseCase(build_geocoder()).execute(payload)


@ordenes_router.post(
    "/{int:orden_servicio_id}/costo",
    response={200: CostoOrdenServicioOut, **ERRORS},
    auth=IngestApiKeyAuth(),
    summary="Calcula y guarda el costo de una orden de servicio",
    description=(
        "Recalcula siempre: da de baja el costo vigente y crea uno nuevo con los "
        "precios congelados al momento del cálculo."
    ),
    operation_id="calcularCostoOrdenServicio",
)
def calcular_costo_orden_servicio(request: HttpRequest, orden_servicio_id: int):
    return 200, CalcularCostoOrdenServicioUseCase.execute(orden_servicio_id)
