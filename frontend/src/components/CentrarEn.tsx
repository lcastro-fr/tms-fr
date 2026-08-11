import { useEffect } from "react";
import { useMap } from "react-leaflet";

import type { LatLng } from "../lib/geojson";

type Props = {
    punto: LatLng | null;
    zoom?: number;
};

/**
 * `MapContainer` sólo honra `center`/`zoom` al montar, así que mover el mapa después pide la
 * API imperativa. `EncuadrarEn` no sirve para un punto: `fitBounds` de un bounds degenerado
 * zoomea al máximo.
 */
export function CentrarEn({ punto, zoom = 15 }: Props) {
    const map = useMap();
    const [lat, lng] = punto ?? [null, null];

    useEffect(() => {
        if (lat === null || lng === null) {
            return;
        }
        const frame = requestAnimationFrame(() => {
            map.setView([lat, lng], Math.max(map.getZoom(), zoom));
        });
        return () => cancelAnimationFrame(frame);
    }, [map, lat, lng, zoom]);

    return null;
}
