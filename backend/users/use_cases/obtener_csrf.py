from __future__ import annotations

from django.http import HttpRequest
from django.middleware.csrf import get_token

from users.dtos import CsrfOut


class ObtenerCsrfUseCase:
    @staticmethod
    def execute(request: HttpRequest) -> CsrfOut:
        return CsrfOut(csrf_token=get_token(request))
