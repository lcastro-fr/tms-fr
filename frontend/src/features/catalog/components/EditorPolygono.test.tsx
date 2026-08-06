import { render } from "@testing-library/react";
import type * as L from "leaflet";
import { StrictMode } from "react";
import { useMap } from "react-leaflet";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { MapaBase } from "../../../components/MapaBase";
import { EditorPolygono } from "./EditorPolygono";

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

beforeAll(() => {
    // jsdom mide todo en cero y Leaflet necesita un tamaño para proyectar.
    Element.prototype.getBoundingClientRect = function () {
        return { width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0 };
    } as never;
});

function montar(valor: typeof CUADRADO | null, onChange: (geom: unknown) => void) {
    let map: L.Map | undefined;

    function Capturar() {
        map = useMap();
        return null;
    }

    const utils = render(
        <StrictMode>
            <MapaBase>
                <Capturar />
                <EditorPolygono valor={valor} onChange={onChange} onMultiPolygon={() => {}} />
            </MapaBase>
        </StrictMode>,
    );

    return { ...utils, map: map! };
}

function poligonoDelMapa(map: L.Map): L.Polygon {
    const capas: L.Polygon[] = [];
    map.eachLayer((capa) => {
        if ("getLatLngs" in capa) {
            capas.push(capa as L.Polygon);
        }
    });
    return capas[0]!;
}

describe("EditorPolygono", () => {
    it("se desmonta sin tocar el mapa que MapContainer ya destruyó", () => {
        // React corre el cleanup del padre antes que el del hijo, así que MapaBase hace
        // map.remove() y recién después corre este cleanup: llamar pm.removeControls() ahí
        // rompía con "Cannot read properties of undefined (reading 'classList')".
        const errores: unknown[] = [];
        const spy = vi.spyOn(console, "error").mockImplementation((...args) => errores.push(args));

        const { unmount } = montar(CUADRADO, () => {});
        unmount();

        spy.mockRestore();
        expect(errores).toEqual([]);
    });

    it("se desmonta con el modo edición todavía activo", () => {
        // El flujo real: se toca Editar, se arrastra un vértice y se guarda sin apagar el
        // modo. El modal cierra, MapContainer mata el mapa y geoman todavía tiene que
        // desarmar sus handles y su hint marker.
        const { map, unmount } = montar(CUADRADO, () => {});
        map.pm.enableGlobalEditMode();

        expect(() => unmount()).not.toThrow();
    });

    it("se desmonta con el modo dibujo todavía activo", () => {
        const { map, unmount } = montar(null, () => {});
        map.pm.enableDraw("Polygon");

        expect(() => unmount()).not.toThrow();
    });

    it("escucha los eventos de edición en la capa, no en el mapa", () => {
        // Geoman dispara pm:update sobre la capa. Con los listeners en el mapa esto no
        // llegaba nunca al formulario y el PUT guardaba la geometría vieja, sin error.
        const onChange = vi.fn();
        const { map } = montar(CUADRADO, onChange);

        poligonoDelMapa(map).fire("pm:update");

        expect(onChange).toHaveBeenCalledTimes(1);
        expect(onChange.mock.calls[0]?.[0]).toMatchObject({ type: "Polygon" });
    });

    it("devuelve el anillo cerrado y en orden GeoJSON", () => {
        const onChange = vi.fn();
        const { map } = montar(CUADRADO, onChange);

        poligonoDelMapa(map).fire("pm:update");

        const anillo = onChange.mock.calls[0]?.[0].coordinates[0];
        expect(anillo[0]).toEqual(anillo.at(-1));
        expect(anillo[0]).toEqual([-58.5, -34.6]);
    });

    it("no emite al adoptar la geometría inicial, que ya está en el formulario", () => {
        const onChange = vi.fn();
        montar(CUADRADO, onChange);

        expect(onChange).not.toHaveBeenCalled();
    });
});
