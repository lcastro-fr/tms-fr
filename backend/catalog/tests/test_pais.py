from __future__ import annotations

import pytest
from django.db.utils import IntegrityError

from catalog.enums import PAIS_LOCAL, DestinoDefault
from catalog.models import Pais, Ubicacion
from catalog.services import PaisService, UbicacionService

pytestmark = pytest.mark.django_db


def ubicacion(codigo: str, **extra) -> Ubicacion:
    return Ubicacion.objects.create(
        codigo=codigo,
        tipo="cliente",
        nombre=f"Destino {codigo}",
        calle="Av. Siempreviva 742",
        localidad="CABA",
        provincia="Buenos Aires",
        **extra,
    )


def test_la_migracion_deja_argentina_cargada():
    assert Pais.objects.get(pk=PAIS_LOCAL).nombre == "Argentina"


@pytest.mark.parametrize("valor", ["AR", "ar", " Ar "])
def test_resolve_encuentra_por_codigo(valor):
    pais = PaisService.resolve(valor)

    assert pais is not None
    assert pais.codigo == PAIS_LOCAL


@pytest.mark.parametrize("valor", ["Argentina", "argentina", " ARGENTINA "])
def test_resolve_cae_al_nombre_cuando_no_es_un_codigo(valor):
    pais = PaisService.resolve(valor)

    assert pais is not None
    assert pais.codigo == PAIS_LOCAL


@pytest.mark.parametrize("valor", ["", None, "Narnia", "Q1"])
def test_resolve_no_inventa_un_pais(valor):
    assert PaisService.resolve(valor) is None


def test_sincronizar_es_idempotente():
    creados, _ = PaisService.sincronizar([("UY", "Uruguay")])
    assert creados == 1

    creados, actualizados = PaisService.sincronizar([("UY", "Uruguay")])
    assert (creados, actualizados) == (0, 1)


def test_no_puede_haber_dos_puertos_por_defecto_activos():
    ubicacion("ARBUE", destino_default=DestinoDefault.PUERTO_MARITIMO.value)

    with pytest.raises(IntegrityError):
        ubicacion("ARROS", destino_default=DestinoDefault.PUERTO_MARITIMO.value)


def test_puerto_y_aeropuerto_conviven():
    ubicacion("ARBUE", destino_default=DestinoDefault.PUERTO_MARITIMO.value)
    ubicacion("AREZE", destino_default=DestinoDefault.AEROPUERTO.value)

    assert (
        UbicacionService.get_ubicacion_by_destino_default_or_raise(
            DestinoDefault.PUERTO_MARITIMO
        ).codigo
        == "ARBUE"
    )
    assert (
        UbicacionService.get_ubicacion_by_destino_default_or_raise(
            DestinoDefault.AEROPUERTO
        ).codigo
        == "AREZE"
    )


def test_dar_de_baja_el_puerto_libera_la_marca():
    viejo = ubicacion("ARBUE", destino_default=DestinoDefault.PUERTO_MARITIMO.value)
    viejo.delete()

    nuevo = ubicacion("ARROS", destino_default=DestinoDefault.PUERTO_MARITIMO.value)

    vigente = UbicacionService.get_ubicacion_by_destino_default(DestinoDefault.PUERTO_MARITIMO)

    assert vigente == nuevo
