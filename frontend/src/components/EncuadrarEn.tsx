import { useEffect } from "react";
import { useMap } from "react-leaflet";

import type { Bounds } from "../lib/geojson";

type Props = {
    bounds: Bounds | null;
};

export function EncuadrarEn({ bounds }: Props) {
    const map = useMap();

    useEffect(() => {
        if (!bounds) {
            return;
        }
        const frame = requestAnimationFrame(() => {
            map.fitBounds(bounds, { padding: [24, 24] });
        });
        return () => cancelAnimationFrame(frame);
    }, [map, bounds]);

    return null;
}
