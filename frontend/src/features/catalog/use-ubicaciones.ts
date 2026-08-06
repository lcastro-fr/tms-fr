import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { usePermisos } from "../auth";
import { ubicacionesQueryOptions } from "./api";
import type { UbicacionOut } from "./api";

type Ubicaciones = {
    puedeVer: boolean;
    mostrar: boolean;
    setMostrar: (mostrar: boolean) => void;
    cargando: boolean;
    fallo: boolean;
    dibujables: UbicacionOut[];
    sinCoordenadas: number;
};

export function useUbicaciones(): Ubicaciones {
    const { can } = usePermisos();
    const puedeVer = can("ubicaciones.ver");
    const [mostrar, setMostrar] = useState(false);

    const query = useQuery({
        ...ubicacionesQueryOptions(),
        enabled: mostrar && puedeVer,
    });

    const dibujables = useMemo(
        () => (query.data ?? []).filter((ubicacion) => ubicacion.coordinates !== null),
        [query.data],
    );

    return {
        puedeVer,
        mostrar,
        setMostrar,
        cargando: query.isFetching,
        fallo: query.isError,
        dibujables,
        sinCoordenadas: (query.data?.length ?? 0) - dibujables.length,
    };
}
