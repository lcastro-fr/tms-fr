import type { components } from "../api/schema";

type GeoJSONMultiPolygon = components["schemas"]["GeoJSONMultiPolygon"];
type GeoJSONPoint = components["schemas"]["GeoJSONPoint"];

export type LatLng = [number, number];
export type Bounds = [LatLng, LatLng];

/** `LatLng[][][]` es lo que `L.polygon()` y `<Polygon positions>` aceptan para un multipolígono. */
export function aLatLngs(geom: GeoJSONMultiPolygon): LatLng[][][] {
    return geom.coordinates.map((poligono) =>
        poligono.map((anillo) => anillo.map(([lng, lat]) => [lat, lng] as LatLng)),
    );
}

export function aLatLng(punto: GeoJSONPoint): LatLng {
    const [lng, lat] = punto.coordinates;
    return [lat, lng];
}

export function cerrarAnillos(coordinates: number[][][][]): number[][][][] {
    return coordinates.map((poligono) =>
        poligono.map((anillo) => {
            const primero = anillo[0];
            const ultimo = anillo[anillo.length - 1];
            if (!primero || !ultimo) {
                return anillo;
            }
            const cerrado = primero[0] === ultimo[0] && primero[1] === ultimo[1];
            return cerrado ? anillo : [...anillo, primero];
        }),
    );
}

export function verticesDistintos(geom: GeoJSONMultiPolygon): number {
    const vistos = new Set<string>();
    for (const poligono of geom.coordinates) {
        for (const anillo of poligono) {
            for (const [lng, lat] of anillo) {
                vistos.add(`${lng},${lat}`);
            }
        }
    }
    return vistos.size;
}

export function boundsDe(geoms: GeoJSONMultiPolygon[]): Bounds | null {
    let sur = Infinity;
    let oeste = Infinity;
    let norte = -Infinity;
    let este = -Infinity;

    for (const geom of geoms) {
        for (const poligono of geom.coordinates) {
            for (const anillo of poligono) {
                for (const [lng, lat] of anillo) {
                    sur = Math.min(sur, lat);
                    norte = Math.max(norte, lat);
                    oeste = Math.min(oeste, lng);
                    este = Math.max(este, lng);
                }
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
