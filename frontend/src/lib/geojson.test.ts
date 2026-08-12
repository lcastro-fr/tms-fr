import { describe, expect, it } from "vitest";

import { aLatLng, aLatLngs, boundsDe, cerrarAnillos, verticesDistintos } from "./geojson";

const CUADRADO = {
    type: "MultiPolygon" as const,
    coordinates: [
        [
            [
                [-58.5, -34.6],
                [-58.4, -34.6],
                [-58.4, -34.5],
                [-58.5, -34.5],
                [-58.5, -34.6],
            ],
        ],
    ],
};

const LEJOS = [
    [
        [-60.0, -33.0],
        [-59.9, -33.0],
        [-59.9, -32.9],
        [-60.0, -33.0],
    ],
];

describe("aLatLngs", () => {
    it("invierte lng/lat de GeoJSON al lat/lng de Leaflet", () => {
        expect(aLatLngs(CUADRADO)[0]?.[0]?.[0]).toEqual([-34.6, -58.5]);
    });

    it("conserva los anillos interiores", () => {
        const conHueco = {
            ...CUADRADO,
            coordinates: [[...CUADRADO.coordinates[0]!, CUADRADO.coordinates[0]![0]!]],
        };
        expect(aLatLngs(conHueco)[0]).toHaveLength(2);
    });

    it("mantiene los polígonos separados, que es lo que Leaflet necesita para no unirlos", () => {
        const dos = { ...CUADRADO, coordinates: [...CUADRADO.coordinates, LEJOS] };
        expect(aLatLngs(dos)).toHaveLength(2);
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
                [
                    [0, 0],
                    [1, 0],
                    [1, 1],
                ],
            ],
        ];
        const anillo = cerrarAnillos(abierto)[0]?.[0];
        expect(anillo).toHaveLength(4);
        expect(anillo?.at(-1)).toEqual([0, 0]);
    });

    it("no duplica el cierre si ya está", () => {
        expect(cerrarAnillos(CUADRADO.coordinates)[0]?.[0]).toHaveLength(5);
    });

    it("cierra todos los polígonos, no sólo el primero", () => {
        const dos = [CUADRADO.coordinates[0]!, [LEJOS[0]!.slice(0, 3)]];
        const cerrados = cerrarAnillos(dos);
        expect(cerrados[1]?.[0]).toHaveLength(4);
    });
});

describe("verticesDistintos", () => {
    it("no cuenta el vértice de cierre", () => {
        expect(verticesDistintos(CUADRADO)).toBe(4);
    });

    it("suma los vértices de todos los polígonos", () => {
        const dos = { ...CUADRADO, coordinates: [...CUADRADO.coordinates, LEJOS] };
        expect(verticesDistintos(dos)).toBe(7);
    });
});

describe("boundsDe", () => {
    it("devuelve el bounding box en orden [[sur, oeste], [norte, este]]", () => {
        expect(boundsDe([CUADRADO])).toEqual([
            [-34.6, -58.5],
            [-34.5, -58.4],
        ]);
    });

    it("abarca todos los polígonos de un multipolígono disjunto", () => {
        const dos = { ...CUADRADO, coordinates: [...CUADRADO.coordinates, LEJOS] };
        expect(boundsDe([dos])).toEqual([
            [-34.6, -60.0],
            [-32.9, -58.4],
        ]);
    });

    it("abarca la unión de varias zonas", () => {
        const otra = { type: "MultiPolygon" as const, coordinates: [LEJOS] };
        expect(boundsDe([CUADRADO, otra])).toEqual([
            [-34.6, -60.0],
            [-32.9, -58.4],
        ]);
    });

    it("devuelve null sin polígonos, para no llamar a fitBounds con basura", () => {
        expect(boundsDe([])).toBeNull();
    });
});
