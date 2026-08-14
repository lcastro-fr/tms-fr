from __future__ import annotations

import pytest

from lib.routing.domain.values import Coordinate, GeocodeQuery, normalizar_pais


def test_la_localidad_se_corta_en_el_guion():
    query = GeocodeQuery(localidad="CABA - Buenos Aires", pais="AR")

    assert query.localidad == "CABA"


def test_una_localidad_en_none_explicito_no_rompe():
    """
    La ingesta la pasa explícita y puede ser None. Pydantic no valida los defaults, así que
    omitir el campo nunca ejercitó este camino: acá revienta con AttributeError, que no es
    un DomainError y se lleva puesta la transacción entera de la ingesta.
    """
    query = GeocodeQuery(direccion="Av. Siempreviva 742", localidad=None, provincia=None, pais="AR")

    assert query.localidad is None
    assert query.as_text() == "Av. Siempreviva 742, AR"


def test_una_localidad_vacia_queda_vacia():
    assert GeocodeQuery(localidad="", pais="AR").localidad == ""


def test_el_pais_se_limpia():
    assert GeocodeQuery(pais="  ar  ").pais == "ar"


@pytest.mark.parametrize("recibido", ["AR", "ar", " ar ", "Argentina", "ARGENTINA"])
def test_los_alias_de_argentina_se_normalizan(recibido: str):
    assert normalizar_pais(recibido) == "Argentina"


@pytest.mark.parametrize("recibido", ["BR", "Brasil", "", "cualquiera"])
def test_un_pais_no_soportado_no_se_normaliza(recibido: str):
    assert normalizar_pais(recibido) is None


def test_as_text_saltea_las_partes_ausentes():
    assert GeocodeQuery(provincia="Santa Fe", pais="AR").as_text() == "Santa Fe, AR"


def test_la_coordenada_va_y_vuelve_en_orden_geojson():
    coordenada = Coordinate.from_lnglat(-58.3816, -34.6037)

    assert coordenada.to_lnglat() == [-58.3816, -34.6037]
    # Point() de Django no acepta Decimal: to_lnglat es el borde que devuelve floats.
    assert all(isinstance(valor, float) for valor in coordenada.to_lnglat())
