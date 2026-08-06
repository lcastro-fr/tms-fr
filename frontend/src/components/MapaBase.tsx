import "leaflet/dist/leaflet.css";

import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { ReactNode } from "react";

import type { LatLng } from "../lib/geojson";
import styles from "./MapaBase.module.css";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const TILE_MAX_ZOOM = 19;

const CENTRO_ARGENTINA: LatLng = [-34.6, -58.45];

type Props = {
    children?: ReactNode;
    center?: LatLng;
    zoom?: number;
};

export function MapaBase({ children, center = CENTRO_ARGENTINA, zoom = 10 }: Props) {
    return (
        <MapContainer center={center} zoom={zoom} className={styles.contenedor}>
            <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} maxZoom={TILE_MAX_ZOOM} />
            <AjustarAlContenedor />
            {children}
        </MapContainer>
    );
}

function AjustarAlContenedor() {
    const map = useMap();

    useEffect(() => {
        const frame = requestAnimationFrame(() => map.invalidateSize());
        const observer = new ResizeObserver(() => map.invalidateSize());
        observer.observe(map.getContainer());
        return () => {
            cancelAnimationFrame(frame);
            observer.disconnect();
        };
    }, [map]);

    return null;
}
