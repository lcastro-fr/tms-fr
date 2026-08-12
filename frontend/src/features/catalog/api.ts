import { queryOptions } from "@tanstack/react-query";

import { http } from "../../api/http";
import type { components } from "../../api/schema";

export type ZonaOut = components["schemas"]["ZonaOut"];
export type ZonaIn = components["schemas"]["ZonaIn"];
export type GeoJSONMultiPolygon = components["schemas"]["GeoJSONMultiPolygon"];
export type UbicacionOut = components["schemas"]["UbicacionOut"];
export type UbicacionIn = components["schemas"]["UbicacionIn"];
export type UbicacionesFilters = components["schemas"]["UbicacionesFilters"];

export type UbicacionesSeleccion = {
    validada?: boolean;
    con_coordenadas?: boolean;
};
export type GeoJSONPoint = components["schemas"]["GeoJSONPoint"];
export type TipoUbicacion = components["schemas"]["TipoUbicacion"];
export type UbicacionCrearIn = components["schemas"]["UbicacionCrearIn"];
export type UbicacionOpcionesOut = components["schemas"]["UbicacionOpcionesOut"];
export type PaisOpcionOut = components["schemas"]["PaisOpcionOut"];
export type GeocodificarUbicacionIn = components["schemas"]["GeocodificarUbicacionIn"];
export type UbicacionGeocodificadaOut = components["schemas"]["UbicacionGeocodificadaOut"];
export type ProvinciaOut = components["schemas"]["ProvinciaOut"];
export type DivisionOut = components["schemas"]["DivisionOut"];
export type UnionDivisionesIn = components["schemas"]["UnionDivisionesIn"];
export type UnionDivisionesOut = components["schemas"]["UnionDivisionesOut"];

export const zonasKeys = {
    all: ["zonas"] as const,
    lista: () => ["zonas", "lista"] as const,
    detail: (id: number) => ["zonas", "detail", id] as const,
};

export const ubicacionesKeys = {
    all: ["ubicaciones"] as const,
    lista: (filters: UbicacionesFilters) => ["ubicaciones", "lista", filters] as const,
    detail: (id: number) => ["ubicaciones", "detail", id] as const,
    opciones: () => ["ubicaciones", "opciones"] as const,
};

export const divisionesKeys = {
    all: ["divisiones"] as const,
    provincias: () => ["divisiones", "provincias"] as const,
    departamentos: (codigo: string) => ["divisiones", "departamentos", codigo] as const,
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

export const ubicacionQueryOptions = (id: number) =>
    queryOptions({
        queryKey: ubicacionesKeys.detail(id),
        queryFn: () => http.get<UbicacionOut>(`/ubicaciones/${id}`).then((r) => r.data),
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

// Tipos de ubicación y países: no cambian mientras dure la sesión.
export const ubicacionesOpcionesQueryOptions = () =>
    queryOptions({
        queryKey: ubicacionesKeys.opciones(),
        queryFn: () =>
            http.get<UbicacionOpcionesOut>("/ubicaciones/opciones").then((r) => r.data),
        staleTime: Infinity,
    });

export async function actualizarUbicacion(
    id: number,
    payload: UbicacionIn,
): Promise<UbicacionOut> {
    const { data } = await http.put<UbicacionOut>(`/ubicaciones/${id}`, payload);
    return data;
}

export async function crearUbicacion(payload: UbicacionCrearIn): Promise<UbicacionOut> {
    const { data } = await http.post<UbicacionOut>("/ubicaciones/", payload);
    return data;
}

/** Preview: no guarda nada, sólo devuelve la coordenada y qué se buscó. */
export async function geocodificarUbicacion(
    payload: GeocodificarUbicacionIn,
): Promise<UbicacionGeocodificadaOut> {
    const { data } = await http.post<UbicacionGeocodificadaOut>(
        "/ubicaciones/geocodificar",
        payload,
    );
    return data;
}

// División política del INDEC (2022): datos maestros de sólo lectura que no cambian.
// La geometría que viaja acá es la simplificada, de dibujo: la unión se calcula en el backend.
export const provinciasQueryOptions = () =>
    queryOptions({
        queryKey: divisionesKeys.provincias(),
        queryFn: () =>
            http.get<ProvinciaOut[]>("/divisiones/provincias").then((r) => r.data),
        staleTime: Infinity,
    });

export const departamentosQueryOptions = (provinciaCodigo: string) =>
    queryOptions({
        queryKey: divisionesKeys.departamentos(provinciaCodigo),
        queryFn: () =>
            http
                .get<DivisionOut[]>(`/divisiones/provincias/${provinciaCodigo}/departamentos`)
                .then((r) => r.data),
        staleTime: Infinity,
    });

/** Preview: no guarda nada, devuelve la geometría que se va a sembrar en el editor. */
export async function unirDivisiones(payload: UnionDivisionesIn): Promise<UnionDivisionesOut> {
    const { data } = await http.post<UnionDivisionesOut>("/divisiones/union", payload);
    return data;
}
