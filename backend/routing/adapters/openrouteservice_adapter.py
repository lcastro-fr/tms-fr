from __future__ import annotations

import openrouteservice
from openrouteservice import exceptions

from routing.domain.exceptions import RoutingError
from routing.domain.ports import Geocoder
from routing.domain.values import Coordinate, GeocodeQuery

DEFAULT_SNAP_RADIUS_M = 2000

_ORS_ERRORS = (
    exceptions.ApiError,
    exceptions.HTTPError,
    exceptions.Timeout,
    exceptions.ValidationError,
)


class OpenRouteServiceAdaptar(Geocoder):
    def __init__(self, api_key: str, snap_radius_m_: int = DEFAULT_SNAP_RADIUS_M):
        if not api_key:
            raise RoutingError(
                "Es necesaria una api key para usar los servicios de open route service"
            )

        self._client = openrouteservice.Client(key=api_key)
        self._snap_radius_m = snap_radius_m_

    def geocode(self, query: GeocodeQuery) -> Coordinate:
        try:
            response = self._client.pelias_structured(
                address=query.direccion,
                locality=query.localidad,
                region=query.provincia,
                country=query.pais,
            )
        except _ORS_ERRORS as e:
            raise RoutingError(f"Ocurrio un error al geolocalizar {query.as_text()}") from e

        features = response.get("features") or []
        if not features:
            raise RoutingError(f"Sin coordenadas para {query.as_text()}. Revise ")
