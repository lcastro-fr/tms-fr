from __future__ import annotations

import pytest

from shared.permisos import PermisoCodigo
from users.models import Permiso, RolPermiso
from users.services import PermisoService

pytestmark = pytest.mark.django_db


def test_une_permisos_de_varios_roles_sin_duplicar(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))
    asignar_rol(user, crear_rol("edicion", PermisoCodigo.ZONAS_VER, PermisoCodigo.ZONAS_EDITAR))

    assert PermisoService.codigos_de_usuario(user) == {
        PermisoCodigo.ZONAS_VER.value,
        PermisoCodigo.ZONAS_EDITAR.value,
    }


def test_superuser_recibe_el_catalogo_completo(crear_usuario, permisos):
    user = crear_usuario(email="admin@tms.test", is_staff=True, is_superuser=True)

    assert PermisoService.codigos_de_usuario(user) == {p.value for p in PermisoCodigo}


def test_usuario_sin_roles_no_tiene_permisos(crear_usuario, permisos):
    assert PermisoService.codigos_de_usuario(crear_usuario()) == set()


def test_usuario_rol_inactivo_no_aporta(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignacion = asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))

    asignacion.delete()

    assert PermisoService.codigos_de_usuario(user) == set()


def test_rol_inactivo_no_aporta(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    rol = crear_rol("lectura", PermisoCodigo.ZONAS_VER)
    asignar_rol(user, rol)

    rol.delete()

    assert PermisoService.codigos_de_usuario(user) == set()


def test_rol_permiso_inactivo_no_aporta(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    rol = crear_rol("lectura", PermisoCodigo.ZONAS_VER)
    asignar_rol(user, rol)

    RolPermiso.objects.get(rol=rol).delete()

    assert PermisoService.codigos_de_usuario(user) == set()


def test_permiso_fuera_del_enum_se_descarta(crear_usuario, crear_rol, asignar_rol):
    """Una fila que quedó de un código retirado no puede llegar al DTO: rompería el 200."""
    user = crear_usuario()
    rol = crear_rol("lectura", PermisoCodigo.ZONAS_VER)
    asignar_rol(user, rol)
    retirado = Permiso.objects.create(codigo="zonas.borrar", descripcion="ya no existe")
    RolPermiso.objects.create(rol=rol, permiso=retirado)

    assert PermisoService.codigos_de_usuario(user) == {PermisoCodigo.ZONAS_VER.value}


def test_nombres_de_roles_ignora_asignaciones_de_baja(crear_usuario, crear_rol, asignar_rol):
    user = crear_usuario()
    asignar_rol(user, crear_rol("lectura", PermisoCodigo.ZONAS_VER))
    baja = asignar_rol(user, crear_rol("edicion", PermisoCodigo.ZONAS_EDITAR))

    baja.delete()

    assert PermisoService.nombres_de_roles(user) == ["lectura"]
