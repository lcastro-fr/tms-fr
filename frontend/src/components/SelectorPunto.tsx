import * as L from "leaflet";
import { useMemo } from "react";
import { Marker, useMapEvents } from "react-leaflet";

import type { components } from "../api/schema";
import { aLatLng, aPunto } from "../lib/geojson";
import styles from "./SelectorPunto.module.css";

type GeoJSONPoint = components["schemas"]["GeoJSONPoint"];

type Props = {
    valor: GeoJSONPoint | null;
    onChange: (punto: GeoJSONPoint) => void;
};

export function SelectorPunto({ valor, onChange }: Props) {
    const icono = useMemo(
        () =>
            L.divIcon({
                className: styles.marcador,
                iconSize: [16, 16],
                iconAnchor: [8, 8],
            }),
        [],
    );

    const emitir = (latlng: L.LatLng) => onChange(aPunto(latlng.lat, latlng.lng));

    useMapEvents({
        click: (evento) => emitir(evento.latlng),
    });

    if (!valor) {
        return null;
    }

    return (
        <Marker
            position={aLatLng(valor)}
            icon={icono}
            draggable
            eventHandlers={{
                dragend: (evento) => emitir(evento.target.getLatLng()),
            }}
        />
    );
}
