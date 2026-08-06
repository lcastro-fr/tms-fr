import * as L from "leaflet";
import { useMemo } from "react";
import { CircleMarker, Tooltip } from "react-leaflet";

import { aLatLng } from "../../../lib/geojson";
import type { UbicacionOut } from "../api";

const COLOR_POR_TIPO: Record<string, string> = {
    planta: "#e03131",
    puerto: "#1971c2",
    aeropuerto: "#6741d9",
    cliente: "#0c8599",
    otro: "#868e96",
};

type Props = {
    ubicaciones: UbicacionOut[];
};

export function CapaUbicaciones({ ubicaciones }: Props) {
    const renderer = useMemo(() => L.canvas({ padding: 0.5 }), []);

    return (
        <>
            {ubicaciones.map((ubicacion) =>
                ubicacion.coordinates === null ? null : (
                    <CircleMarker
                        key={ubicacion.id}
                        center={aLatLng(ubicacion.coordinates)}
                        renderer={renderer}
                        radius={4}
                        pathOptions={{
                            color: COLOR_POR_TIPO[ubicacion.tipo] ?? COLOR_POR_TIPO.otro,
                            fillOpacity: 0.8,
                            weight: 1,
                        }}
                    >
                        <Tooltip>
                            {ubicacion.codigo
                                ? `${ubicacion.nombre} (${ubicacion.codigo})`
                                : ubicacion.nombre}
                        </Tooltip>
                    </CircleMarker>
                ),
            )}
        </>
    );
}
