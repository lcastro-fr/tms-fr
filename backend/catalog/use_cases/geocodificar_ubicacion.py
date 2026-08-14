from __future__ import annotations

from catalog.dtos import GeocodificarUbicacionIn, GeoJSONPoint, UbicacionGeocodificadaOut
from catalog.services import PaisService
from lib.routing.domain import GeocodeQuery, Geocoder, GeocoderNoConfiguradoError, RoutingError
from shared.exceptions import BusinessRuleError


class GeocodificarUbicacionUseCase:
    """
    Preview: no escribe nada. Recibe el geocoder por constructor, igual que la ingesta, para
    que los tests inyecten uno falso y no toquen la red.
    """

    class PaisInvalidoError(BusinessRuleError):
        pass

    class GeolocalizacionNoDisponibleError(BusinessRuleError):
        pass

    class GeolocalizacionFallidaError(BusinessRuleError):
        pass

    def __init__(self, geocoder: Geocoder) -> None:
        self._geocoder = geocoder

    def execute(self, data: GeocodificarUbicacionIn) -> UbicacionGeocodificadaOut:
        pais = PaisService.get_pais(data.pais_codigo)
        if pais is None:
            raise GeocodificarUbicacionUseCase.PaisInvalidoError(
                f"No existe el país con código {data.pais_codigo!r}",
                detail={"campo": "pais_codigo", "codigo": data.pais_codigo},
            )

        query = GeocodeQuery(
            direccion=data.calle,
            localidad=data.localidad,
            provincia=data.provincia,
            pais=pais.codigo,
        )

        try:
            coordinate = self._geocoder.geocode(query=query)
        except GeocoderNoConfiguradoError as exc:
            # Sin esta rama el mensaje que llega al browser nombra ORS_API_KEY.
            raise GeocodificarUbicacionUseCase.GeolocalizacionNoDisponibleError(
                "La geolocalización automática no está disponible. Marcá el punto en el mapa.",
                detail={"motivo": "no_configurado"},
            ) from exc
        except RoutingError as exc:
            raise GeocodificarUbicacionUseCase.GeolocalizacionFallidaError(
                str(exc),
                detail={"motivo": "geocoder", "consulta": query.as_text()},
            ) from exc

        return UbicacionGeocodificadaOut(
            coordinates=GeoJSONPoint(coordinates=coordinate.to_lnglat()),
            consulta=query.as_text(),
        )
