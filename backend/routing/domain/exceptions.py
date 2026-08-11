class RoutingError(Exception):
    """Base routing error"""


class GeocoderNoConfiguradoError(RoutingError):
    """No hay proveedor de geocoding. Separada para no filtrar el nombre de la variable."""
