import { useEffect } from "react";
import { useMap } from "react-leaflet";

import type { Bounds } from "../lib/geojson";

type Props = {
    bounds: Bounds | null;
};

export function EncuadrarEn({ bounds }: Props) {
    const map = useMap();

    useEffect(() => {
        // fitBounds con bounds inválidos tira, y adentro de un effect eso es un error
        // boundary en blanco, no un warning en consola.
        if (!bounds) {
            return;
        }
        // Adentro de un Modal el contenedor todavía mide 0px en este punto, y encuadrar
        // sobre un mapa sin tamaño da un zoom absurdo. El rAF lo deja correr después del
        // invalidateSize de MapaBase.
        const frame = requestAnimationFrame(() => {
            map.fitBounds(bounds, { padding: [24, 24] });
        });
        return () => cancelAnimationFrame(frame);
    }, [map, bounds]);

    return null;
}
