import { queryOptions } from "@tanstack/react-query";

import { http } from "../../api/http";
import type { components } from "../../api/schema";

export type ZonaOut = components["schemas"]["ZonaOut"];
export type ZonaIn = components["schemas"]["ZonaIn"];
export type GeoJSONPolygon = components["schemas"]["GeoJSONPolygon"];
export type UbicacionOut = components["schemas"]["UbicacionOut"];
export type UbicacionIn = components["schemas"]["UbicacionIn"];
export type UbicacionesFilters = components["schemas"]["UbicacionesFilters"];

export type UbicacionesSeleccion = {
    validada?: boolean;
    con_coordenadas?: boolean;
};
export type GeoJSONPoint = components["schemas"]["GeoJSONPoint"];
export type TipoUbicacion = components["schemas"]["TipoUbicacion"];

export const zonasKeys = {
    all: ["zonas"] as const,
    lista: () => ["zonas", "lista"] as const,
    detail: (id: number) => ["zonas", "detail", id] as const,
};

export const ubicacionesKeys = {
    all: ["ubicaciones"] as const,
    lista: (filters: UbicacionesFilters) => ["ubicaciones", "lista", filters] as const,
};

export const zonasQueryOptions = () =>
    queryOptions({
        queryKey: zonasKeys.lista(),
        queryFn: () => http.get<ZonaOut[]>("/zonas/").then((r) => r.data),
    });

export const zonaQueryOptions = (id: number) =>
    queryOptions({
        queryKey: zonasKeys.detail(id),
        queryFn: () => http.get<ZonaOut>(`/zonas/${id}`).then((r) => r.data),
    });

export const ubicacionesQueryOptions = (filters: UbicacionesFilters = {}) =>
    queryOptions({
        queryKey: ubicacionesKeys.lista(filters),
        queryFn: () =>
            http.get<UbicacionOut[]>("/ubicaciones/", { params: filters }).then((r) => r.data),
        staleTime: 5 * 60_000,
    });

export async function crearZona(payload: ZonaIn): Promise<ZonaOut> {
    const { data } = await http.post<ZonaOut>("/zonas/", payload);
    return data;
}

export async function actualizarZona(id: number, payload: ZonaIn): Promise<ZonaOut> {
    const { data } = await http.put<ZonaOut>(`/zonas/${id}`, payload);
    return data;
}

export async function eliminarZona(id: number): Promise<void> {
    await http.delete(`/zonas/${id}`);
}

export async function actualizarUbicacion(
    id: number,
    payload: UbicacionIn,
): Promise<UbicacionOut> {
    const { data } = await http.put<UbicacionOut>(`/ubicaciones/${id}`, payload);
    return data;
}
