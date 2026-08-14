from __future__ import annotations
from abc import ABC, abstractmethod

from typing import Any


class SAPProtocol(ABC):
    @abstractmethod
    def __init__(self, endpoint: str, username: str, password: str) -> None:
        self.endpoint: str = endpoint
        self.username: str = username
        self.password: str = password

    @abstractmethod
    def call_rfc(self, rfc_name: str, params: dict[str, Any]) -> dict[str, Any]: ...
