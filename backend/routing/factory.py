from __future__ import annotations

from django.conf import settings

from routing.adapters import OpenRouteServiceAdapter
from routing.domain.exceptions import GeocoderNoConfiguradoError
from routing.domain.ports import Geocoder
from routing.domain.values import Coordinate, GeocodeQuery


class GeocoderNoConfigurado(Geocoder):
    def geocode(self, query: GeocodeQuery) -> Coordinate:
        raise GeocoderNoConfiguradoError("No hay ORS_API_KEY configurada: no se puede geolocalizar")


def build_geocoder() -> Geocoder:
    if not settings.ORS_API_KEY:
        return GeocoderNoConfigurado()
    return OpenRouteServiceAdapter(api_key=settings.ORS_API_KEY)
