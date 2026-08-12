import { render } from "@testing-library/react";
import type * as L from "leaflet";
import { StrictMode } from "react";
import { useMap } from "react-leaflet";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { MapaBase } from "../../../components/MapaBase";
import { EditorPolygono } from "./EditorPolygono";
import type { Semilla } from "./EditorPolygono";

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

const DISJUNTOS = {
    type: "MultiPolygon" as const,
    coordinates: [
        ...CUADRADO.coordinates,
        [
            [
                [-60.5, -32.6],
                [-60.4, -32.6],
                [-60.4, -32.5],
                [-60.5, -32.5],
                [-60.5, -32.6],
            ],
        ],
    ],
};

beforeAll(() => {
    Element.prototype.getBoundingClientRect = function () {
        return { width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0 };
    } as never;
});

function montar(
    valor: typeof CUADRADO | null,
    onChange: (geom: unknown) => void,
    semilla: Semilla | null = null,
) {
    let map: L.Map | undefined;

    function Capturar() {
        map = useMap();
        return null;
    }

    const utils = render(
        <StrictMode>
            <MapaBase>
                <Capturar />
                <EditorPolygono valor={valor} semilla={semilla} onChange={onChange} />
            </MapaBase>
        </StrictMode>,
    );

    const rerender = (nueva: Semilla | null) =>
        utils.rerender(
            <StrictMode>
                <MapaBase>
                    <Capturar />
                    <EditorPolygono valor={valor} semilla={nueva} onChange={onChange} />
                </MapaBase>
            </StrictMode>,
        );

    return { ...utils, rerender, map: map! };
}

function poligonosDelMapa(map: L.Map): L.Polygon[] {
    const capas: L.Polygon[] = [];
    map.eachLayer((capa) => {
        if ("getLatLngs" in capa) {
            capas.push(capa as L.Polygon);
        }
    });
    return capas;
}

describe("EditorPolygono", () => {
    it("se desmonta sin tocar el mapa que MapContainer ya destruyó", () => {
        const errores: unknown[] = [];
        const spy = vi.spyOn(console, "error").mockImplementation((...args) => errores.push(args));

        const { unmount } = montar(CUADRADO, () => {});
        unmount();

        spy.mockRestore();
        expect(errores).toEqual([]);
    });

    it("se desmonta con el modo edición todavía activo", () => {
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
        const onChange = vi.fn();
        const { map } = montar(CUADRADO, onChange);

        poligonosDelMapa(map)[0]!.fire("pm:update");

        expect(onChange).toHaveBeenCalledTimes(1);
        expect(onChange.mock.calls[0]?.[0]).toMatchObject({ type: "MultiPolygon" });
    });

    it("emite MultiPolygon aunque la capa tenga un solo polígono", () => {
        const onChange = vi.fn();
        const { map } = montar(CUADRADO, onChange);

        poligonosDelMapa(map)[0]!.fire("pm:update");

        expect(onChange.mock.calls[0]?.[0].coordinates).toHaveLength(1);
    });

    it("devuelve el anillo cerrado y en orden GeoJSON", () => {
        const onChange = vi.fn();
        const { map } = montar(CUADRADO, onChange);

        poligonosDelMapa(map)[0]!.fire("pm:update");

        const anillo = onChange.mock.calls[0]?.[0].coordinates[0][0];
        expect(anillo[0]).toEqual(anillo.at(-1));
        expect(anillo[0]).toEqual([-58.5, -34.6]);
    });

    it("dibuja los dos polígonos de una zona disjunta en una sola capa", () => {
        const onChange = vi.fn();
        const { map } = montar(DISJUNTOS, onChange);

        const capas = poligonosDelMapa(map);
        expect(capas).toHaveLength(1);
        poligonosDelMapa(map)[0]!.fire("pm:update");
        expect(onChange.mock.calls[0]?.[0].coordinates).toHaveLength(2);
    });

    it("no emite al adoptar la geometría inicial, que ya está en el formulario", () => {
        const onChange = vi.fn();
        montar(CUADRADO, onChange);

        expect(onChange).not.toHaveBeenCalled();
    });

    it("una semilla nueva reemplaza la geometría y la emite", () => {
        const onChange = vi.fn();
        const { rerender } = montar(CUADRADO, onChange);

        rerender({ geom: DISJUNTOS, version: 1 });

        expect(onChange).toHaveBeenCalled();
        expect(onChange.mock.lastCall?.[0].coordinates).toHaveLength(2);
    });

    it("la misma version no re-siembra, así una edición a mano no se pisa", () => {
        const onChange = vi.fn();
        const { rerender } = montar(CUADRADO, onChange, { geom: DISJUNTOS, version: 1 });
        onChange.mockClear();

        rerender({ geom: DISJUNTOS, version: 1 });

        expect(onChange).not.toHaveBeenCalled();
    });
});
