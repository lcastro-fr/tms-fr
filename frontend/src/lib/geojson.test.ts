import { describe, expect, it } from "vitest";

import { aLatLng, aLatLngs, boundsDe, cerrarAnillos, verticesDistintos } from "./geojson";

const CUADRADO = {
    type: "Polygon" as const,
    coordinates: [
        [
            [-58.5, -34.6],
            [-58.4, -34.6],
            [-58.4, -34.5],
            [-58.5, -34.5],
            [-58.5, -34.6],
        ],
    ],
};

describe("aLatLngs", () => {
    it("invierte lng/lat de GeoJSON al lat/lng de Leaflet", () => {
        expect(aLatLngs(CUADRADO)[0]?.[0]).toEqual([-34.6, -58.5]);
    });

    it("conserva los anillos interiores", () => {
        const conHueco = {
            ...CUADRADO,
            coordinates: [...CUADRADO.coordinates, CUADRADO.coordinates[0]!],
        };
        expect(aLatLngs(conHueco)).toHaveLength(2);
    });
});

describe("aLatLng", () => {
    it("invierte un punto", () => {
        expect(aLatLng({ type: "Point", coordinates: [-60.6393, -32.9468] })).toEqual([
            -32.9468, -60.6393,
        ]);
    });
});

describe("cerrarAnillos", () => {
    it("agrega el vértice de cierre cuando falta", () => {
        const abierto = [
            [
                [0, 0],
                [1, 0],
                [1, 1],
            ],
        ];
        const [anillo] = cerrarAnillos(abierto);
        expect(anillo).toHaveLength(4);
        expect(anillo?.at(-1)).toEqual([0, 0]);
    });

    it("no duplica el cierre si ya está", () => {
        expect(cerrarAnillos(CUADRADO.coordinates)[0]).toHaveLength(5);
    });
});

describe("verticesDistintos", () => {
    it("no cuenta el vértice de cierre", () => {
        expect(verticesDistintos(CUADRADO)).toBe(4);
    });
});

describe("boundsDe", () => {
    it("devuelve el bounding box en orden [[sur, oeste], [norte, este]]", () => {
        expect(boundsDe([CUADRADO])).toEqual([
            [-34.6, -58.5],
            [-34.5, -58.4],
        ]);
    });

    it("abarca la unión de varios polígonos", () => {
        const otro = {
            type: "Polygon" as const,
            coordinates: [
                [
                    [-60.0, -33.0],
                    [-59.9, -33.0],
                    [-59.9, -32.9],
                    [-60.0, -33.0],
                ],
            ],
        };
        expect(boundsDe([CUADRADO, otro])).toEqual([
            [-34.6, -60.0],
            [-32.9, -58.4],
        ]);
    });

    it("devuelve null sin polígonos, para no llamar a fitBounds con basura", () => {
        expect(boundsDe([])).toBeNull();
    });
});
