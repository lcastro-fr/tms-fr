import "leaflet/dist/leaflet.css";

import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { ReactNode } from "react";

import type { LatLng } from "../lib/geojson";
import styles from "./MapaBase.module.css";

// Un solo lugar para el proveedor de tiles: cambiarlo no debería tocar nada más.
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
    // Sin preferCanvas: con el renderer de canvas un Polygon no tiene `_path` y geoman le
    // cuelga sus clases al <canvas> compartido. Los puntos traen su propio canvas.
    return (
        <MapContainer center={center} zoom={zoom} className={styles.contenedor}>
            <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} maxZoom={TILE_MAX_ZOOM} />
            <AjustarAlContenedor />
            {children}
        </MapContainer>
    );
}

// Dentro de un Modal el mapa se monta antes de que el contenedor tenga tamaño: sin esto
// queda un tile en la esquina y gris el resto, sin ningún error.
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
