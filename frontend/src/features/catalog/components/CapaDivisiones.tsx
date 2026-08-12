import { useMantineTheme } from "@mantine/core";
import { useMemo } from "react";
import { Polygon, Tooltip } from "react-leaflet";

import { EncuadrarEn } from "../../../components/EncuadrarEn";
import { aLatLngs, boundsDe } from "../../../lib/geojson";
import type { DivisionOut } from "../api";

type Props = {
    divisiones: DivisionOut[];
    marcados: Set<string>;
    onToggle: (codigo: string) => void;
};

export function CapaDivisiones({ divisiones, marcados, onToggle }: Props) {
    const theme = useMantineTheme();
    const color = theme.colors[theme.primaryColor]?.[6] ?? theme.colors.blue[6];

    // Encuadra sobre todo lo dibujado, así agregar una provincia al alcance no deja sus
    // departamentos fuera de pantalla. `divisiones` sólo cambia cuando cambia el alcance o
    // termina de cargar una provincia, que son los dos momentos en que corresponde reencuadrar;
    // componer la geometría mueve el bounds de EditorPolygono, no este.
    const bounds = useMemo(() => boundsDe(divisiones.map((d) => d.geom)), [divisiones]);

    return (
        <>
            <EncuadrarEn bounds={bounds} />
            {divisiones.map((division) => {
                const marcado = marcados.has(division.codigo);
                return (
                    <Polygon
                        key={division.codigo}
                        positions={aLatLngs(division.geom)}
                        eventHandlers={{ click: () => onToggle(division.codigo) }}
                        pathOptions={{
                            color,
                            weight: marcado ? 2 : 1,
                            opacity: marcado ? 1 : 0.5,
                            fillOpacity: marcado ? 0.35 : 0.05,
                        }}
                    >
                        <Tooltip sticky>{division.nombre}</Tooltip>
                    </Polygon>
                );
            })}
        </>
    );
}
