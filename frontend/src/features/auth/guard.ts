import { redirect } from "@tanstack/react-router";

import type { PermisoCodigo, SesionOut } from "./api";

export function requirePermiso(
    sesion: SesionOut,
    permiso: PermisoCodigo,
): void {
    if (!sesion.permisos.includes(permiso)) {
        throw redirect({ to: "/" });
    }
}
