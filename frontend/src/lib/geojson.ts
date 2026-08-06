import type { components } from "../api/schema";

type GeoJSONPolygon = components["schemas"]["GeoJSONPolygon"];
type GeoJSONPoint = components["schemas"]["GeoJSONPoint"];

export type LatLng = [number, number];
export type Bounds = [LatLng, LatLng];

export function aLatLngs(geom: GeoJSONPolygon): LatLng[][] {
    return geom.coordinates.map((anillo) => anillo.map(([lng, lat]) => [lat, lng] as LatLng));
}

export function aLatLng(punto: GeoJSONPoint): LatLng {
    const [lng, lat] = punto.coordinates;
    return [lat, lng];
}

export function cerrarAnillos(coordinates: number[][][]): number[][][] {
    return coordinates.map((anillo) => {
        const primero = anillo[0];
        const ultimo = anillo[anillo.length - 1];
        if (!primero || !ultimo) {
            return anillo;
        }
        const cerrado = primero[0] === ultimo[0] && primero[1] === ultimo[1];
        return cerrado ? anillo : [...anillo, primero];
    });
}

export function verticesDistintos(geom: GeoJSONPolygon): number {
    const anillo = geom.coordinates[0] ?? [];
    return new Set(anillo.map(([lng, lat]) => `${lng},${lat}`)).size;
}

export function boundsDe(geoms: GeoJSONPolygon[]): Bounds | null {
    let sur = Infinity;
    let oeste = Infinity;
    let norte = -Infinity;
    let este = -Infinity;

    for (const geom of geoms) {
        for (const anillo of geom.coordinates) {
            for (const [lng, lat] of anillo) {
                sur = Math.min(sur, lat);
                norte = Math.max(norte, lat);
                oeste = Math.min(oeste, lng);
                este = Math.max(este, lng);
            }
        }
    }

    if (norte === -Infinity) {
        return null;
    }
    return [
        [sur, oeste],
        [norte, este],
    ];
}
