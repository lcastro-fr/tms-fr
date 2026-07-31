from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from core.auth import IngestApiKeyAuth
from shared.dtos import ERRORS
from tracking.dtos import TicketIngestIn, TicketIngestOut
from tracking.use_cases import IngestTicketUseCase

router = Router(tags=["tickets"])


@router.post(
    "/ingest",
    response={201: TicketIngestOut, **ERRORS},
    auth=IngestApiKeyAuth(),
    summary="Ingesta de un ticket",
    operation_id="ingestTicket",
)
def ingest_ticket(request: HttpRequest, payload: TicketIngestIn):
    return 201, IngestTicketUseCase.execute(payload)
