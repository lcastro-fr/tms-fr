import { queryOptions } from "@tanstack/react-query";

import { http } from "../../api/http";
import type { components } from "../../api/schema";

export type ZonaOut = components["schemas"]["ZonaOut"];
export type ZonaIn = components["schemas"]["ZonaIn"];
export type GeoJSONPolygon = components["schemas"]["GeoJSONPolygon"];
export type UbicacionOut = components["schemas"]["UbicacionOut"];

export const zonasKeys = {
    all: ["zonas"] as const,
    lista: () => ["zonas", "lista"] as const,
    detail: (id: number) => ["zonas", "detail", id] as const,
};

export const ubicacionesKeys = {
    all: ["ubicaciones"] as const,
    lista: () => ["ubicaciones", "lista"] as const,
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

// Datos maestros: no hace falta revalidarlos cada 30s como el resto.
export const ubicacionesQueryOptions = () =>
    queryOptions({
        queryKey: ubicacionesKeys.lista(),
        queryFn: () => http.get<UbicacionOut[]>("/ubicaciones/").then((r) => r.data),
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
