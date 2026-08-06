import { render } from "@testing-library/react";
import * as L from "leaflet";
import { useMap } from "react-leaflet";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { MapaBase } from "./MapaBase";
import { SelectorPunto } from "./SelectorPunto";

const PUNTO = { type: "Point" as const, coordinates: [-58.3816, -34.6037] };

beforeAll(() => {
    Element.prototype.getBoundingClientRect = function () {
        return { width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0 };
    } as never;
});

function montar(valor: typeof PUNTO | null, onChange: (punto: unknown) => void) {
    let map: L.Map | undefined;

    function Capturar() {
        map = useMap();
        return null;
    }

    render(
        <MapaBase>
            <Capturar />
            <SelectorPunto valor={valor} onChange={onChange} />
        </MapaBase>,
    );

    return map!;
}

function marcadorDelMapa(map: L.Map): L.Marker | undefined {
    let encontrado: L.Marker | undefined;
    map.eachLayer((capa) => {
        if ("getLatLng" in capa) {
            encontrado = capa as L.Marker;
        }
    });
    return encontrado;
}

describe("SelectorPunto", () => {
    it("emite el punto en orden GeoJSON al clickear el mapa", () => {
        const onChange = vi.fn();
        const map = montar(null, onChange);

        map.fire("click", { latlng: { lat: -34.6037, lng: -58.3816 } });

        expect(onChange).toHaveBeenCalledWith({
            type: "Point",
            coordinates: [-58.3816, -34.6037],
        });
    });

    it("sin coordenada no dibuja marcador", () => {
        const map = montar(null, () => {});

        expect(marcadorDelMapa(map)).toBeUndefined();
    });

    it("con coordenada pone el marcador en el lugar correcto", () => {
        const map = montar(PUNTO, () => {});

        const latlng = marcadorDelMapa(map)?.getLatLng();
        expect(latlng?.lat).toBeCloseTo(-34.6037);
        expect(latlng?.lng).toBeCloseTo(-58.3816);
    });

    it("arrastrar el marcador emite el punto nuevo", () => {
        const onChange = vi.fn();
        const map = montar(PUNTO, onChange);
        const marcador = marcadorDelMapa(map)!;

        marcador.setLatLng([-31.4201, -64.1888]);
        marcador.fire("dragend", { target: marcador } as never);

        expect(onChange).toHaveBeenCalledWith({
            type: "Point",
            coordinates: [-64.1888, -31.4201],
        });
    });

    it("el marcador es arrastrable y usa un divIcon, no el ícono default", () => {
        const marcador = marcadorDelMapa(montar(PUNTO, () => {}));

        expect(marcador?.options.draggable).toBe(true);
        expect(marcador?.options.icon).toBeInstanceOf(L.DivIcon);
        expect(marcador?.options.icon?.options.className).toBeTruthy();
    });
});
