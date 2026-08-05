import type { ReactNode } from "react";

import type { PermisoCodigo } from "../api";
import { usePermisos } from "../permisos";

type Props = {
    permiso: PermisoCodigo;
    children: ReactNode;
    fallback?: ReactNode;
};

export function Can({ permiso, children, fallback = null }: Props) {
    const { can } = usePermisos();
    return <>{can(permiso) ? children : fallback}</>;
}
