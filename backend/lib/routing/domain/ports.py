from __future__ import annotations

from typing import Protocol

from lib.routing.domain.values import Coordinate, GeocodeQuery


class Geocoder(Protocol):
    def geocode(self, query: GeocodeQuery) -> Coordinate: ...
