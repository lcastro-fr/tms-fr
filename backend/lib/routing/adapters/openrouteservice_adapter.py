from __future__ import annotations

import openrouteservice
from openrouteservice import exceptions

from lib.routing.domain.exceptions import RoutingError
from lib.routing.domain.ports import Geocoder
from lib.routing.domain.values import Coordinate, GeocodeQuery, normalizar_pais

_ORS_ERRORS = (
    exceptions.ApiError,
    exceptions.HTTPError,
    exceptions.Timeout,
    exceptions.ValidationError,
)


class OpenRouteServiceAdapter(Geocoder):
    def __init__(self, api_key: str):
        if not api_key:
            raise RoutingError(
                "Es necesaria una api key para usar los servicios de open route service"
            )

        self._client = openrouteservice.Client(key=api_key)

    def geocode(self, query: GeocodeQuery) -> Coordinate:
        pais = normalizar_pais(query.pais)
        if pais is None:
            raise RoutingError(f"País no soportado para geolocalizar: {query.pais!r}")

        try:
            response = self._client.pelias_structured(
                address=query.direccion,
                locality=query.localidad,
                region=query.provincia,
                country=pais,
            )
        except _ORS_ERRORS as e:
            raise RoutingError(f"Ocurrio un error al geolocalizar {query.as_text()}") from e

        features = response.get("features") or []
        if not features:
            raise RoutingError(f"Sin coordenadas para {query.as_text()}")

        try:
            lng, lat = features[0]["geometry"]["coordinates"][:2]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise RoutingError(
                f"Respuesta inesperada de open route service para {query.as_text()}"
            ) from e

        return Coordinate.from_lnglat(lng, lat)
