from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from catalog.enums import TipoCamion
from shared.permisos import PermisoCodigo
from transportista.enums import ModalidadFlete
from transportista.models import TarifaConceptoAdicional, TarifaFlete, Tarifario

from .conftest import VIGENTE_DESDE

pytestmark = pytest.mark.django_db

TARIFARIOS = "/api/v1/tarifarios/"

TODOS = (
    PermisoCodigo.TARIFARIOS_VER,
    PermisoCodigo.TARIFARIOS_CREAR,
    PermisoCodigo.TARIFARIOS_EDITAR,
    PermisoCodigo.TARIFARIOS_ELIMINAR,
)


def flete_in(zona_id=None, ubicacion_id=None, **extra) -> dict:
    return {
        "zona_id": zona_id,
        "ubicacion_id": ubicacion_id,
        "modalidad": extra.pop("modalidad", ModalidadFlete.DIRECTO.value),
        "tipo_camion": extra.pop("tipo_camion", TipoCamion.SEMI.value),
        "hombreador": extra.pop("hombreador", False),
        "precio": extra.pop("precio", "185000.00"),
    }


def tarifario_in(transportista, fletes=None, conceptos=None, **extra) -> dict:
    return {
        "transportista_id": transportista.id,
        "vigente_desde": extra.pop("vigente_desde", VIGENTE_DESDE.isoformat()),
        "vigente_hasta": extra.pop("vigente_hasta", None),
        "tarifas_flete": fletes or [],
        "tarifas_concepto": conceptos or [],
    }


def crear(client, transportista, **kwargs):
    return client.post(
        TARIFARIOS, tarifario_in(transportista, **kwargs), content_type="application/json"
    )


# --- auth -------------------------------------------------------------------


def test_sin_sesion_da_401(client):
    assert client.get(TARIFARIOS).status_code == 401


def test_logueado_sin_permiso_da_403_y_no_401(client, usuario_con, transportista):
    client.force_login(usuario_con(PermisoCodigo.TARIFARIOS_VER))

    resp = crear(client, transportista)

    assert resp.status_code == 403
    assert resp.json()["error"]["detail"]["requiere"] == [PermisoCodigo.TARIFARIOS_CREAR.value]


def test_id_inexistente_da_404(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.TARIFARIOS_VER))

    resp = client.get(f"{TARIFARIOS}9999")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


# --- alta -------------------------------------------------------------------


def test_crea_el_tarifario_y_sus_dos_colecciones(
    client, usuario_con, transportista, zona, ubicacion, concepto
):
    client.force_login(usuario_con(*TODOS))

    resp = crear(
        client,
        transportista,
        fletes=[
            flete_in(zona_id=zona.id),
            flete_in(ubicacion_id=ubicacion.id, precio="210000.00"),
        ],
        conceptos=[{"concepto_id": concepto.id, "precio": "1000.00"}],
    )

    assert resp.status_code == 201
    cuerpo = resp.json()
    assert len(cuerpo["tarifas_flete"]) == 2
    assert len(cuerpo["tarifas_concepto"]) == 1
    assert cuerpo["cantidad_fletes"] == 2
    assert cuerpo["en_uso"] is False
    assert cuerpo["tarifas_concepto"][0]["concepto_codigo"] == concepto.codigo

    por_alcance = {t["zona_nombre"] or t["ubicacion_codigo"]: t for t in cuerpo["tarifas_flete"]}
    # El Decimal viaja como string.
    assert por_alcance[zona.nombre]["precio"] == "185000.00"
    assert por_alcance[ubicacion.codigo]["precio"] == "210000.00"


def test_los_fletes_salen_siempre_en_el_mismo_orden(
    client, usuario_con, transportista, zona, ubicacion
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(
        client,
        transportista,
        fletes=[
            flete_in(ubicacion_id=ubicacion.id),
            flete_in(zona_id=zona.id),
            flete_in(zona_id=zona.id, hombreador=True),
        ],
    ).json()

    ids = [t["id"] for t in creado["tarifas_flete"]]
    for _ in range(3):
        detalle = client.get(f"{TARIFARIOS}{creado['id']}").json()
        assert [t["id"] for t in detalle["tarifas_flete"]] == ids


def test_flete_con_zona_y_ubicacion_a_la_vez_da_payload_invalid(
    client, usuario_con, transportista, zona, ubicacion
):
    client.force_login(usuario_con(*TODOS))

    resp = crear(
        client, transportista, fletes=[flete_in(zona_id=zona.id, ubicacion_id=ubicacion.id)]
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"
    assert Tarifario.objects.count() == 0


def test_flete_sin_zona_ni_ubicacion_da_payload_invalid(client, usuario_con, transportista):
    client.force_login(usuario_con(*TODOS))

    resp = crear(client, transportista, fletes=[flete_in()])

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


def test_dos_fletes_con_la_misma_clave_dan_conflict(client, usuario_con, transportista, zona):
    client.force_login(usuario_con(*TODOS))

    resp = crear(
        client, transportista, fletes=[flete_in(zona_id=zona.id), flete_in(zona_id=zona.id)]
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"
    assert resp.json()["error"]["detail"]["coleccion"] == "tarifas_flete"
    assert Tarifario.objects.count() == 0


def test_una_zona_inexistente_da_business_rule_y_no_500(client, usuario_con, transportista):
    client.force_login(usuario_con(*TODOS))

    resp = crear(client, transportista, fletes=[flete_in(zona_id=9999)])

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "business_rule"
    assert resp.json()["error"]["detail"]["campo"] == "zona_id"


def test_vigencia_solapada_da_conflict(client, usuario_con, transportista, zona):
    client.force_login(usuario_con(*TODOS))
    primero = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)])

    resp = crear(client, transportista)

    assert resp.status_code == 409
    assert resp.json()["error"]["detail"]["tarifario_id"] == primero.json()["id"]


def test_vigencia_invertida_da_business_rule(client, usuario_con, transportista):
    client.force_login(usuario_con(*TODOS))

    resp = crear(
        client,
        transportista,
        vigente_desde=datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
        vigente_hasta=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "business_rule"


def test_una_fecha_naive_da_payload_invalid(client, usuario_con, transportista):
    client.force_login(usuario_con(*TODOS))

    resp = crear(client, transportista, vigente_desde="2026-01-01T00:00:00")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payload_invalid"


# --- edición ----------------------------------------------------------------


def test_el_put_reemplaza_los_hijos_dando_de_baja_los_viejos(
    client, usuario_con, transportista, zona, ubicacion
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    vieja_id = creado["tarifas_flete"][0]["id"]

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(
            transportista, fletes=[flete_in(ubicacion_id=ubicacion.id, precio="999000.00")]
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert [t["ubicacion_id"] for t in resp.json()["tarifas_flete"]] == [ubicacion.id]
    assert TarifaFlete.all_objects.filter(pk=vieja_id, active=False).exists()


def test_el_put_puede_recrear_la_misma_clave_recien_dada_de_baja(
    client, usuario_con, transportista, zona
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(transportista, fletes=[flete_in(zona_id=zona.id, precio="200000.00")]),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.json()["tarifas_flete"][0]["precio"] == "200000.00"
    assert TarifaFlete.objects.filter(tarifario_id=creado["id"]).count() == 1


def test_el_put_puede_mover_el_tarifario_a_otro_transportista(
    client, usuario_con, transportista, otro_transportista, zona
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(otro_transportista, fletes=[flete_in(zona_id=zona.id)]),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.json()["transportista_razon_social"] == otro_transportista.razon_social


# --- tarifario en uso -------------------------------------------------------


def test_un_tarifario_en_uso_no_permite_cambiar_el_precio_de_una_fila(
    client, usuario_con, transportista, zona, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]))

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(transportista, fletes=[flete_in(zona_id=zona.id, precio="1.00")]),
        content_type="application/json",
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["detail"]["motivo"] == "congelada"
    assert TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]).precio == 185000


def test_un_tarifario_en_uso_no_permite_cambiar_el_precio_de_un_concepto(
    client, usuario_con, transportista, concepto, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(
        client, transportista, conceptos=[{"concepto_id": concepto.id, "precio": "1000.00"}]
    ).json()
    costear(
        tarifa_concepto=TarifaConceptoAdicional.objects.get(pk=creado["tarifas_concepto"][0]["id"])
    )

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(
            transportista, conceptos=[{"concepto_id": concepto.id, "precio": "5000.00"}]
        ),
        content_type="application/json",
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["detail"]["motivo"] == "congelada"


def test_un_tarifario_en_uso_no_permite_quitar_una_fila(
    client, usuario_con, transportista, zona, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]))

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(transportista),
        content_type="application/json",
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["detail"]["motivo"] == "quitada"
    assert TarifaFlete.objects.filter(tarifario_id=creado["id"]).count() == 1


def test_un_tarifario_en_uso_permite_agregar_una_tarifa_de_flete(
    client, usuario_con, transportista, zona, ubicacion, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    congelada = TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"])
    costo = costear(tarifa_flete=congelada)

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(
            transportista,
            fletes=[
                flete_in(zona_id=zona.id),
                flete_in(ubicacion_id=ubicacion.id, precio="90000.00"),
            ],
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.json()["en_uso"] is True
    fletes = resp.json()["tarifas_flete"]
    assert len(fletes) == 2
    assert {t["zona_id"] for t in fletes} == {zona.id, None}
    congelada.refresh_from_db()
    assert congelada.precio == 185000
    costo.refresh_from_db()
    assert costo.precio_flete == 185000
    assert costo.tarifa_flete_id == congelada.id


def test_un_tarifario_en_uso_permite_agregar_un_concepto(
    client, usuario_con, transportista, zona, concepto, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]))

    resp = client.put(
        f"{TARIFARIOS}{creado['id']}",
        tarifario_in(
            transportista,
            fletes=[flete_in(zona_id=zona.id)],
            conceptos=[{"concepto_id": concepto.id, "precio": "1000.00"}],
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert [t["concepto_id"] for t in resp.json()["tarifas_concepto"]] == [concepto.id]


def test_un_tarifario_en_uso_no_se_da_de_baja(client, usuario_con, transportista, zona, costear):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]))

    resp = client.delete(f"{TARIFARIOS}{creado['id']}")

    assert resp.status_code == 409
    assert Tarifario.objects.filter(pk=creado["id"]).exists()


def test_un_tarifario_en_uso_si_puede_cerrar_su_vigencia(
    client, usuario_con, transportista, zona, costear
):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=creado["tarifas_flete"][0]["id"]))
    cierre = datetime(2026, 12, 31, tzinfo=UTC)

    resp = client.post(
        f"{TARIFARIOS}{creado['id']}/cerrar",
        {"vigente_hasta": cierre.isoformat()},
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.json()["en_uso"] is True
    assert Tarifario.objects.get(pk=creado["id"]).vigente_hasta == cierre


def test_cerrado_el_viejo_se_puede_crear_uno_nuevo(client, usuario_con, transportista, zona):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    client.post(
        f"{TARIFARIOS}{creado['id']}/cerrar",
        {"vigente_hasta": datetime(2026, 6, 30, tzinfo=UTC).isoformat()},
        content_type="application/json",
    )

    resp = crear(
        client,
        transportista,
        vigente_desde=datetime(2026, 7, 1, tzinfo=UTC).isoformat(),
        fletes=[flete_in(zona_id=zona.id)],
    )

    assert resp.status_code == 201


# --- lista y baja -----------------------------------------------------------


def test_la_lista_marca_en_uso_solo_al_que_corresponde(
    client, usuario_con, transportista, otro_transportista, zona, costear
):
    client.force_login(usuario_con(*TODOS))
    usado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    libre = crear(client, otro_transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    costear(tarifa_flete=TarifaFlete.objects.get(pk=usado["tarifas_flete"][0]["id"]))

    por_id = {t["id"]: t for t in client.get(TARIFARIOS).json()}

    assert por_id[usado["id"]]["en_uso"] is True
    assert por_id[libre["id"]]["en_uso"] is False
    assert por_id[libre["id"]]["cantidad_fletes"] == 1


def test_el_filtro_de_vencidos_es_tri_estado(client, usuario_con, transportista, zona):
    client.force_login(usuario_con(*TODOS))
    ayer = timezone.now() - timedelta(days=1)
    vencido = crear(
        client,
        transportista,
        vigente_desde=(ayer - timedelta(days=30)).isoformat(),
        fletes=[flete_in(zona_id=zona.id)],
    ).json()
    client.post(
        f"{TARIFARIOS}{vencido['id']}/cerrar",
        {"vigente_hasta": ayer.isoformat()},
        content_type="application/json",
    )
    en_pie = crear(
        client,
        transportista,
        vigente_desde=timezone.now().isoformat(),
        fletes=[flete_in(zona_id=zona.id)],
    ).json()

    def ids(**params):
        return sorted(t["id"] for t in client.get(TARIFARIOS, params).json())

    assert ids() == sorted([vencido["id"], en_pie["id"]])
    assert ids(vencidos="false") == [en_pie["id"]]
    # false es "sólo los que siguen en pie", no "sin filtro".
    assert ids(vencidos="true") == [vencido["id"]]


def test_uno_que_arranca_en_el_futuro_no_se_esconde(client, usuario_con, transportista, zona):
    """Cargar un tarifario con fecha futura y que desaparezca de la lista sería el peor caso."""
    client.force_login(usuario_con(*TODOS))

    futuro = crear(
        client,
        transportista,
        vigente_desde=(timezone.now() + timedelta(days=30)).isoformat(),
        fletes=[flete_in(zona_id=zona.id)],
    ).json()

    ids = [t["id"] for t in client.get(TARIFARIOS, {"vencidos": "false"}).json()]
    assert futuro["id"] in ids


def test_la_lista_filtra_por_transportista(
    client, usuario_con, transportista, otro_transportista, zona
):
    client.force_login(usuario_con(*TODOS))
    crear(client, transportista, fletes=[flete_in(zona_id=zona.id)])
    crear(client, otro_transportista, fletes=[flete_in(zona_id=zona.id)])

    resp = client.get(TARIFARIOS, {"transportista_id": transportista.id})

    assert [t["transportista_id"] for t in resp.json()] == [transportista.id]


def test_la_baja_es_logica_y_arrastra_los_hijos(client, usuario_con, transportista, zona, concepto):
    client.force_login(usuario_con(*TODOS))
    creado = crear(
        client,
        transportista,
        fletes=[flete_in(zona_id=zona.id)],
        conceptos=[{"concepto_id": concepto.id, "precio": "1000.00"}],
    ).json()

    resp = client.delete(f"{TARIFARIOS}{creado['id']}")

    assert resp.status_code == 204
    assert client.get(TARIFARIOS).json() == []
    assert Tarifario.all_objects.filter(pk=creado["id"], active=False).exists()
    assert not TarifaFlete.objects.filter(tarifario_id=creado["id"]).exists()
    assert not TarifaConceptoAdicional.objects.filter(tarifario_id=creado["id"]).exists()


def test_dada_de_baja_se_libera_la_vigencia_abierta(client, usuario_con, transportista, zona):
    client.force_login(usuario_con(*TODOS))
    creado = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)]).json()
    client.delete(f"{TARIFARIOS}{creado['id']}")

    resp = crear(client, transportista, fletes=[flete_in(zona_id=zona.id)])

    assert resp.status_code == 201


# --- opciones ---------------------------------------------------------------


def test_las_opciones_traen_todo_lo_que_el_formulario_necesita(
    client, usuario_con, transportista, zona, ubicacion, concepto
):
    client.force_login(usuario_con(PermisoCodigo.TARIFARIOS_VER))

    cuerpo = client.get(f"{TARIFARIOS}opciones").json()

    assert [m["value"] for m in cuerpo["modalidades"]] == [m.value for m in ModalidadFlete]
    assert [t["value"] for t in cuerpo["tipos_camion"]] == [t.value for t in TipoCamion]
    assert [t["id"] for t in cuerpo["transportistas"]] == [transportista.id]
    assert [c["id"] for c in cuerpo["conceptos"]] == [concepto.id]
    assert [z["id"] for z in cuerpo["zonas"]] == [zona.id]
    assert [u["id"] for u in cuerpo["ubicaciones"]] == [ubicacion.id]


def test_las_opciones_no_piden_permiso_de_zonas_ni_de_ubicaciones(client, usuario_con):
    client.force_login(usuario_con(PermisoCodigo.TARIFARIOS_VER))

    assert client.get(f"{TARIFARIOS}opciones").status_code == 200
