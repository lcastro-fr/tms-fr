from __future__ import annotations

import pytest

from shared.permisos import PermisoCodigo
from users.models import Permiso
from users.services import PermisoService

pytestmark = pytest.mark.django_db


def test_crea_una_fila_por_codigo_del_enum():
    creados, actualizados, retirados = PermisoService.sincronizar()

    assert creados == len(PermisoCodigo)
    assert actualizados == 0
    assert retirados == []
    assert set(Permiso.objects.values_list("codigo", flat=True)) == {p.value for p in PermisoCodigo}


def test_es_idempotente():
    PermisoService.sincronizar()

    creados, actualizados, _ = PermisoService.sincronizar()

    assert creados == 0
    assert actualizados == len(PermisoCodigo)
    assert Permiso.objects.count() == len(PermisoCodigo)


def test_da_de_baja_los_codigos_retirados():
    PermisoService.sincronizar()
    Permiso.objects.create(codigo="zonas.borrar", descripcion="ya no existe")

    _, _, retirados = PermisoService.sincronizar()

    assert retirados == ["zonas.borrar"]
    assert not Permiso.all_objects.get(codigo="zonas.borrar").active
    assert Permiso.objects.count() == len(PermisoCodigo)
