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

export function aPunto(lat: number, lng: number): GeoJSONPoint {
    return { type: "Point", coordinates: [lng, lat] };
}

/** ≈0,1 m. Leaflet devuelve ~15 dígitos y llenar un input con eso es ruido. */
export function redondearCoordenada(valor: number): number {
    return Math.round(valor * 1e6) / 1e6;
}

const PAR_LAT_LNG = /^\s*(-?\d+(?:\.\d+)?)\s*(?:,\s*|\s+)(-?\d+(?:\.\d+)?)\s*$/;

/** El formato que copia Google Maps: latitud primero, decimales con punto. */
export function parsearParLatLng(texto: string): LatLng | null {
    const match = PAR_LAT_LNG.exec(texto);
    if (!match) {
        return null;
    }
    const lat = Number(match[1]);
    const lng = Number(match[2]);
    if (Math.abs(lat) > 90 || Math.abs(lng) > 180) {
        return null;
    }
    return [redondearCoordenada(lat), redondearCoordenada(lng)];
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
