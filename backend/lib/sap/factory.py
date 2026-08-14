from __future__ import annotations

from django.conf import settings

from lib.sap.adapters.soap_adapter import Saponoso
from lib.sap.ports.sap_ports import SAPProtocol

def build_sap_protocol() -> SAPProtocol:
    """Builds the SAP protocol based on the settings."""
    required = ["SAP_ENDPOINT", "SAP_USERNAME", "SAP_PASSWORD"]
    for r in required:
        if not hasattr(settings, r):
            raise ValueError(f"Missing required setting: {r}")

    return Saponoso(
        endpoint=settings.SAP_ENDPOINT,
        username=settings.SAP_USERNAME,
        password=settings.SAP_PASSWORD,
    )
