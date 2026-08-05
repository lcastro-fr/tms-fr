from __future__ import annotations

from enum import StrEnum


# Vive en shared/ y no en users/: ponerlo allá obligaría a catalog a importar users.
class PermisoCodigo(StrEnum):
    ZONAS_VER = "zonas.ver"
    ZONAS_CREAR = "zonas.crear"
    ZONAS_EDITAR = "zonas.editar"


PERMISO_CHOICES = [(p.value, p.value) for p in PermisoCodigo]

PERMISO_DESCRIPCIONES: dict[PermisoCodigo, str] = {
    PermisoCodigo.ZONAS_VER: "Ver zonas",
    PermisoCodigo.ZONAS_CREAR: "Crear zonas",
    PermisoCodigo.ZONAS_EDITAR: "Editar zonas",
}
