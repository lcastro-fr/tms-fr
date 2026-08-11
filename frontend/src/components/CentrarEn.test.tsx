import { render } from "@testing-library/react";
import type * as L from "leaflet";
import { useMap } from "react-leaflet";
import { beforeAll, describe, expect, it } from "vitest";

import { CentrarEn } from "./CentrarEn";
import { MapaBase } from "./MapaBase";
import type { LatLng } from "../lib/geojson";

beforeAll(() => {
    Element.prototype.getBoundingClientRect = function () {
        return { width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0 };
    } as never;
});

function montar(punto: LatLng | null, zoom?: number) {
    let map: L.Map | undefined;

    function Capturar() {
        map = useMap();
        return null;
    }

    const utils = render(
        <MapaBase center={[-34.6, -58.45]} zoom={4}>
            <Capturar />
            <CentrarEn punto={punto} zoom={zoom} />
        </MapaBase>,
    );

    return { map: map!, utils };
}

describe("CentrarEn", () => {
    it("mueve el mapa al punto", async () => {
        const { map } = montar([-32.9442, -60.6393]);

        await new Promise((resolver) => requestAnimationFrame(() => resolver(null)));

        expect(map.getCenter().lat).toBeCloseTo(-32.9442, 3);
        expect(map.getCenter().lng).toBeCloseTo(-60.6393, 3);
    });

    it("acerca el zoom cuando estaba más lejos", async () => {
        const { map } = montar([-32.9442, -60.6393], 15);

        await new Promise((resolver) => requestAnimationFrame(() => resolver(null)));

        expect(map.getZoom()).toBe(15);
    });

    it("sin punto deja el mapa donde estaba", async () => {
        // Tolerancia baja porque el invalidateSize de MapaBase recentra unos metros solo.
        const { map } = montar(null);

        await new Promise((resolver) => requestAnimationFrame(() => resolver(null)));

        expect(map.getCenter().lat).toBeCloseTo(-34.6, 1);
        expect(map.getCenter().lng).toBeCloseTo(-58.45, 1);
        expect(map.getZoom()).toBe(4);
    });

    it("no aleja el mapa si el usuario ya estaba más cerca", async () => {
        const { map } = montar([-32.9442, -60.6393], 15);
        await new Promise((resolver) => requestAnimationFrame(() => resolver(null)));
        map.setZoom(18);

        expect(map.getZoom()).toBe(18);
    });
});
