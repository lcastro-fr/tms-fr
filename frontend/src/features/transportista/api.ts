import { queryOptions } from "@tanstack/react-query";

import { http } from "../../api/http";
import type { components } from "../../api/schema";

export type TarifarioOut = components["schemas"]["TarifarioOut"];
export type TarifarioDetalleOut = components["schemas"]["TarifarioDetalleOut"];
export type TarifarioIn = components["schemas"]["TarifarioIn"];
export type CerrarTarifarioIn = components["schemas"]["CerrarTarifarioIn"];
export type TarifariosFilters = components["schemas"]["TarifariosFilters"];
export type TarifaFleteIn = components["schemas"]["TarifaFleteIn"];
export type TarifaFleteOut = components["schemas"]["TarifaFleteOut"];
export type TarifaConceptoIn = components["schemas"]["TarifaConceptoIn"];
export type TarifaConceptoOut = components["schemas"]["TarifaConceptoOut"];
export type TarifarioOpcionesOut = components["schemas"]["TarifarioOpcionesOut"];
export type ConceptoAdicionalOut = components["schemas"]["ConceptoAdicionalOut"];
export type ModalidadFlete = components["schemas"]["ModalidadFlete"];
export type TipoCamion = components["schemas"]["TipoCamion"];

/**
 * Más angosto que el DTO: sin `null`, que duplicaría la entrada de cache y volvería como
 * el string "null" en la URL. `incluir_historicos` está invertido respecto de la API porque
 * la pantalla arranca escondiendo los vencidos: el control se nombra por lo que agrega.
 */
export type TarifariosSeleccion = {
    transportista_id?: number;
    incluir_historicos?: boolean;
};

export const tarifariosKeys = {
    all: ["tarifarios"] as const,
    lista: (filters: TarifariosFilters) => ["tarifarios", "lista", filters] as const,
    detail: (id: number) => ["tarifarios", "detail", id] as const,
    opciones: () => ["tarifarios", "opciones"] as const,
};

function aFiltros({
    incluir_historicos,
    ...resto
}: TarifariosSeleccion): TarifariosFilters {
    return { ...resto, vencidos: incluir_historicos ? undefined : false };
}

export const tarifariosQueryOptions = (seleccion: TarifariosSeleccion = {}) => {
    const filters = aFiltros(seleccion);
    return queryOptions({
        queryKey: tarifariosKeys.lista(filters),
        queryFn: () =>
            http.get<TarifarioOut[]>("/tarifarios/", { params: filters }).then((r) => r.data),
    });
};

export const tarifarioQueryOptions = (id: number) =>
    queryOptions({
        queryKey: tarifariosKeys.detail(id),
        queryFn: () =>
            http.get<TarifarioDetalleOut>(`/tarifarios/${id}`).then((r) => r.data),
    });

export const tarifarioOpcionesQueryOptions = () =>
    queryOptions({
        queryKey: tarifariosKeys.opciones(),
        queryFn: () =>
            http.get<TarifarioOpcionesOut>("/tarifarios/opciones").then((r) => r.data),
        staleTime: Infinity,
    });

export async function crearTarifario(payload: TarifarioIn): Promise<TarifarioDetalleOut> {
    const { data } = await http.post<TarifarioDetalleOut>("/tarifarios/", payload);
    return data;
}

export async function actualizarTarifario(
    id: number,
    payload: TarifarioIn,
): Promise<TarifarioDetalleOut> {
    const { data } = await http.put<TarifarioDetalleOut>(`/tarifarios/${id}`, payload);
    return data;
}

export async function cerrarTarifario(
    id: number,
    payload: CerrarTarifarioIn,
): Promise<TarifarioOut> {
    const { data } = await http.post<TarifarioOut>(`/tarifarios/${id}/cerrar`, payload);
    return data;
}

export async function eliminarTarifario(id: number): Promise<void> {
    await http.delete(`/tarifarios/${id}`);
}
