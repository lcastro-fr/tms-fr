from __future__ import annotations

from shared.permisos import PERMISO_DESCRIPCIONES, PermisoCodigo
from users.models import Permiso, User


class PermisoService:
    @staticmethod
    def list_permisos() -> list[Permiso]:
        return list(Permiso.objects.all())

    @staticmethod
    def codigos_de_usuario(user: User) -> set[str]:
        if user.is_superuser:
            return {p.value for p in PermisoCodigo}

        codigos = Permiso.objects.filter(
            rol_permisos__active=True,
            rol_permisos__rol__active=True,
            rol_permisos__rol__usuario_roles__active=True,
            rol_permisos__rol__usuario_roles__usuario=user,
        ).values_list("codigo", flat=True)

        vigentes = {p.value for p in PermisoCodigo}
        return {c for c in codigos if c in vigentes}

    @staticmethod
    def nombres_de_roles(user: User) -> list[str]:
        return list(
            user.roles.filter(active=True, usuario_roles__active=True)
            .order_by("nombre")
            .values_list("nombre", flat=True)
            .distinct()
        )

    @staticmethod
    def sincronizar() -> tuple[int, int, list[str]]:
        """Upsert de una fila por miembro del enum. Da de baja las que ya no existen."""
        creados = actualizados = 0

        for codigo in PermisoCodigo:
            descripcion = PERMISO_DESCRIPCIONES.get(codigo, "")
            _, creado = Permiso.objects.update_or_create(
                codigo=codigo.value,
                defaults={"descripcion": descripcion},
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        vigentes = [p.value for p in PermisoCodigo]
        retirados = list(
            Permiso.objects.exclude(codigo__in=vigentes).values_list("codigo", flat=True)
        )
        if retirados:
            Permiso.objects.exclude(codigo__in=vigentes).delete()

        return creados, actualizados, retirados
