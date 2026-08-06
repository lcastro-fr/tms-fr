from __future__ import annotations

import pytest

from logistica.services import OrdenServicioService
from transportista.enums import ModalidadFlete, Via

pytestmark = pytest.mark.django_db


def test_todos_nacionales_pasan_derecho(crear_orden, crear_ubicacion):
    orden = crear_orden(via=Via.TERRESTRE.value)
    destinos = [crear_ubicacion("CL100"), crear_ubicacion("CL200")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == destinos


def test_un_extranjero_por_via_maritima_sale_por_el_puerto(crear_orden, crear_ubicacion, puerto):
    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [crear_ubicacion("CL999", pais="UY")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == [puerto]


def test_un_extranjero_por_via_aerea_sale_por_el_aeropuerto(
    crear_orden, crear_ubicacion, aeropuerto
):
    orden = crear_orden(via=Via.AEREA.value)
    destinos = [crear_ubicacion("CL999", pais="UY")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == [aeropuerto]


def test_varios_extranjeros_colapsan_en_un_solo_destino(crear_orden, crear_ubicacion, puerto):
    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [
        crear_ubicacion("CL997", pais="UY"),
        crear_ubicacion("CL998", pais="BR"),
        crear_ubicacion("CL999", pais="CL"),
    ]

    resueltos = OrdenServicioService.resolve_destinos(orden, destinos)

    assert resueltos == [puerto]
    assert ModalidadFlete.para_destinos(len(resueltos)) is ModalidadFlete.DIRECTO


def test_un_nacional_y_un_extranjero_dan_dos_destinos(crear_orden, crear_ubicacion, puerto):
    orden = crear_orden(via=Via.MARITIMA.value)
    nacional = crear_ubicacion("CL100")
    destinos = [nacional, crear_ubicacion("CL999", pais="UY")]

    resueltos = OrdenServicioService.resolve_destinos(orden, destinos)

    assert resueltos == [nacional, puerto]
    assert ModalidadFlete.para_destinos(len(resueltos)) is ModalidadFlete.MULTIPARADA


def test_el_puerto_no_se_duplica_si_ya_era_un_destino(crear_orden, crear_ubicacion, puerto):
    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [puerto, crear_ubicacion("CL999", pais="UY")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == [puerto]


def test_terrestre_con_un_extranjero_no_sabe_a_donde_ir(crear_orden, crear_ubicacion):
    orden = crear_orden(via=Via.TERRESTRE.value)
    destinos = [crear_ubicacion("CL100"), crear_ubicacion("CL999", pais="UY")]

    with pytest.raises(OrdenServicioService.ViaSinDestinoDefaultError) as exc:
        OrdenServicioService.resolve_destinos(orden, destinos)

    assert exc.value.detail["motivo"] == "via_sin_destino_default"
    assert exc.value.detail["codigos"] == ["CL999"]
    assert exc.value.status_code == 422


def test_terrestre_con_todos_nacionales_no_pide_destino_default(crear_orden, crear_ubicacion):
    orden = crear_orden(via=Via.TERRESTRE.value)
    destinos = [crear_ubicacion("CL100")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == destinos


def test_un_destino_sin_pais_no_se_adivina(crear_orden, crear_ubicacion):
    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [crear_ubicacion("CL999", pais=None)]

    with pytest.raises(OrdenServicioService.DestinoSinPaisError) as exc:
        OrdenServicioService.resolve_destinos(orden, destinos)

    assert exc.value.detail["motivo"] == "sin_pais"
    assert exc.value.detail["codigos"] == ["CL999"]


def test_sin_ubicacion_marcada_como_puerto_da_not_found(crear_orden, crear_ubicacion):
    from catalog.services import UbicacionService

    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [crear_ubicacion("CL999", pais="UY")]

    with pytest.raises(UbicacionService.DestinoDefaultNotFoundError) as exc:
        OrdenServicioService.resolve_destinos(orden, destinos)

    assert exc.value.status_code == 404


def test_cambiar_la_via_cambia_el_destino_sin_cache(
    crear_orden, crear_ubicacion, puerto, aeropuerto
):
    orden = crear_orden(via=Via.MARITIMA.value)
    destinos = [crear_ubicacion("CL999", pais="UY")]

    assert OrdenServicioService.resolve_destinos(orden, destinos) == [puerto]

    orden.via = Via.AEREA.value
    orden.save(update_fields=["via", "updated_at"])

    assert OrdenServicioService.resolve_destinos(orden, destinos) == [aeropuerto]
