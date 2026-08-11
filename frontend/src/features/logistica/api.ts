import { queryOptions } from "@tanstack/react-query";

import { http } from "../../api/http";
import type { components } from "../../api/schema";

export type OrdenServicioOut = components["schemas"]["OrdenServicioOut"];
export type OrdenServicioIn = components["schemas"]["OrdenServicioIn"];
export type OrdenesServicioFilters =
    components["schemas"]["OrdenesServicioFilters"];
export type OrdenServicioOpcionesOut =
    components["schemas"]["OrdenServicioOpcionesOut"];
export type CostoOrdenServicioOut =
    components["schemas"]["CostoOrdenServicioOut"];
export type OpcionOut = components["schemas"]["OpcionOut"];
export type OrdenServicioDetalleOut =
    components["schemas"]["OrdenServicioDetalleOut"];
export type TicketOut = components["schemas"]["TicketOut"];
export type RemitoOut = components["schemas"]["RemitoOut"];
export type RemitoDestinoOut = components["schemas"]["RemitoDestinoOut"];
export type OrdenServicioDestinoIn =
    components["schemas"]["OrdenServicioDestinoIn"];
export type OrdenServicioDestinoOut =
    components["schemas"]["OrdenServicioDestinoOut"];
export type UbicacionOpcionOut = components["schemas"]["UbicacionOpcionOut"];

// Más angosta que el DTO a propósito: un null en el search viaja como el string "null"
// y además duplica la entrada de cache. Las fechas van como "YYYY-MM-DD".
export type OrdenesServicioSeleccion = {
    incluir_no_facturables?: boolean;
    con_costo?: boolean;
    numero?: string;
    fecha_viaje_desde?: string;
    fecha_viaje_hasta?: string;
    incluir_sin_fecha?: boolean;
};

function aFiltros({
    incluir_no_facturables,
    ...resto
}: OrdenesServicioSeleccion): OrdenesServicioFilters {
    return { ...resto, facturable: incluir_no_facturables ? undefined : true };
}

export const ordenesServicioKeys = {
    all: ["ordenes-servicio"] as const,
    lista: (filters: OrdenesServicioFilters) =>
        ["ordenes-servicio", "lista", filters] as const,
    detail: (id: number) => ["ordenes-servicio", "detail", id] as const,
    opciones: () => ["ordenes-servicio", "opciones"] as const,
};

export const ordenesServicioQueryOptions = (
    seleccion: OrdenesServicioSeleccion = {},
) => {
    const filters = aFiltros(seleccion);
    return queryOptions({
        queryKey: ordenesServicioKeys.lista(filters),
        queryFn: () =>
            http
                .get<
                    OrdenServicioOut[]
                >("/ordenes-servicio/", { params: filters })
                .then((r) => r.data),
    });
};

export const ordenServicioQueryOptions = (id: number) =>
    queryOptions({
        queryKey: ordenesServicioKeys.detail(id),
        queryFn: () =>
            http
                .get<OrdenServicioDetalleOut>(`/ordenes-servicio/${id}`)
                .then((r) => r.data),
    });

// Son enums del backend: no cambian mientras dure la sesión.
export const opcionesOrdenServicioQueryOptions = () =>
    queryOptions({
        queryKey: ordenesServicioKeys.opciones(),
        queryFn: () =>
            http
                .get<OrdenServicioOpcionesOut>("/ordenes-servicio/opciones")
                .then((r) => r.data),
        staleTime: Infinity,
    });

export async function actualizarOrdenServicio(
    id: number,
    payload: OrdenServicioIn,
): Promise<OrdenServicioOut> {
    const { data } = await http.put<OrdenServicioOut>(
        `/ordenes-servicio/${id}`,
        payload,
    );
    return data;
}

export async function calcularCostoOrdenServicio(
    id: number,
): Promise<CostoOrdenServicioOut> {
    const { data } = await http.post<CostoOrdenServicioOut>(
        `/ordenes-servicio/${id}/costo`,
    );
    return data;
}
