from __future__ import annotations

from enum import StrEnum


# Vive en shared/ y no en users/: ponerlo allá obligaría a catalog a importar users.
class PermisoCodigo(StrEnum):
    ZONAS_VER = "zonas.ver"
    ZONAS_CREAR = "zonas.crear"
    ZONAS_EDITAR = "zonas.editar"
    ZONAS_ELIMINAR = "zonas.eliminar"
    UBICACIONES_VER = "ubicaciones.ver"
    UBICACIONES_EDITAR = "ubicaciones.editar"
    ORDENES_SERVICIO_VER = "ordenes_servicio.ver"
    ORDENES_SERVICIO_EDITAR = "ordenes_servicio.editar"
    ORDENES_SERVICIO_CALCULAR_COSTO = "ordenes_servicio.calcular_costo"


PERMISO_CHOICES = [(p.value, p.value) for p in PermisoCodigo]

PERMISO_DESCRIPCIONES: dict[PermisoCodigo, str] = {
    PermisoCodigo.ZONAS_VER: "Ver zonas",
    PermisoCodigo.ZONAS_CREAR: "Crear zonas",
    PermisoCodigo.ZONAS_EDITAR: "Editar zonas",
    PermisoCodigo.ZONAS_ELIMINAR: "Eliminar zonas",
    PermisoCodigo.UBICACIONES_VER: "Ver ubicaciones",
    PermisoCodigo.UBICACIONES_EDITAR: "Editar y validar ubicaciones",
    PermisoCodigo.ORDENES_SERVICIO_VER: "Ver órdenes de servicio",
    PermisoCodigo.ORDENES_SERVICIO_EDITAR: "Editar órdenes de servicio",
    PermisoCodigo.ORDENES_SERVICIO_CALCULAR_COSTO: "Calcular el costo de una orden de servicio",
}
