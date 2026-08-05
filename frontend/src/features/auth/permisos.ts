import { useRouteContext } from "@tanstack/react-router";
import { useMemo } from "react";

import type { PermisoCodigo, SesionOut } from "./api";

type Permisos = {
    sesion: SesionOut;
    can: (permiso: PermisoCodigo) => boolean;
    canAlguno: (...permisos: PermisoCodigo[]) => boolean;
};

// Lectura síncrona: el beforeLoad de _authenticated ya resolvió la sesión.
export function usePermisos(): Permisos {
    const { sesion } = useRouteContext({ from: "/_authenticated" });

    return useMemo(() => {
        const codigos = new Set<PermisoCodigo>(sesion.permisos);
        return {
            sesion,
            can: (permiso) => codigos.has(permiso),
            canAlguno: (...permisos) => permisos.some((p) => codigos.has(p)),
        };
    }, [sesion]);
}
