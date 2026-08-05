from __future__ import annotations

import pytest

from shared.permisos import PermisoCodigo
from users.models import RolPermiso, UsuarioRol

pytestmark = pytest.mark.django_db


def test_baja_de_rol_arrastra_asignaciones_y_permisos(crear_usuario, crear_rol, asignar_rol):
    """
    La razón de ser de las tablas de relación propias: con la intermedia automática de
    Django estas filas no tienen columna active y sobrevivirían a la baja del rol.
    """
    user = crear_usuario()
    rol = crear_rol("lectura", PermisoCodigo.ZONAS_VER, PermisoCodigo.ZONAS_EDITAR)
    asignacion = asignar_rol(user, rol)

    rol.delete()

    assert not UsuarioRol.all_objects.get(pk=asignacion.pk).active
    assert RolPermiso.all_objects.filter(rol=rol, active=True).count() == 0
    assert RolPermiso.all_objects.filter(rol=rol).count() == 2


def test_baja_de_permiso_arrastra_su_vinculo_con_el_rol(crear_rol, permisos):
    crear_rol("lectura", PermisoCodigo.ZONAS_VER)
    permiso = permisos[PermisoCodigo.ZONAS_VER.value]

    permiso.delete()

    assert RolPermiso.all_objects.filter(permiso=permiso, active=True).count() == 0


def test_la_baja_libera_la_unique_parcial(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    rol = crear_rol("lectura", PermisoCodigo.ZONAS_VER)
    asignar_rol(user, rol).delete()

    reasignado = asignar_rol(user, rol)

    assert reasignado.active
