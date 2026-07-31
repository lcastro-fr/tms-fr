from __future__ import annotations

import hmac

from django.conf import settings
from django.http import HttpRequest
from ninja.security import APIKeyHeader


class IngestApiKeyAuth(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request: HttpRequest, key: str | None) -> str | None:
        expected = settings.INGEST_API_KEY
        if not key or not expected:
            return None
        if not hmac.compare_digest(key, expected):
            return None
        return "ingest"
