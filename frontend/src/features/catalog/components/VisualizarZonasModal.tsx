import { Badge, Group, Modal, Stack, useMantineTheme } from "@mantine/core";
import { useMemo } from "react";
import { Polygon, Tooltip } from "react-leaflet";

import { EncuadrarEn } from "../../../components/EncuadrarEn";
import { MapaBase } from "../../../components/MapaBase";
import { aLatLngs, boundsDe } from "../../../lib/geojson";
import type { ZonaOut } from "../api";
import { useUbicaciones } from "../use-ubicaciones";
import { CapaUbicaciones } from "./CapaUbicaciones";
import { ControlUbicaciones } from "./ControlUbicaciones";

const TOPE_ETIQUETAS_FIJAS = 5;

type Props = {
    zonas: ZonaOut[];
    onClose: () => void;
};

export function VisualizarZonasModal({ zonas, onClose }: Props) {
    const theme = useMantineTheme();
    const ubicaciones = useUbicaciones();
    const bounds = useMemo(() => boundsDe(zonas.map((zona) => zona.geom)), [zonas]);

    const colorDe = (indice: number) => {
        const paleta = theme.other.zonaPalette;
        const nombre = paleta[indice % paleta.length] ?? theme.primaryColor;
        return theme.colors[nombre]?.[6] ?? theme.colors.blue[6];
    };

    return (
        <Modal
            opened
            onClose={onClose}
            size="80rem"
            title={zonas.length === 1 ? zonas[0]?.nombre : `${zonas.length} zonas`}
        >
            <Stack gap="md">
                <Group gap="xs">
                    {zonas.map((zona, indice) => (
                        <Badge key={zona.id} color={colorDe(indice)}>
                            {zona.nombre}
                        </Badge>
                    ))}
                </Group>

                <ControlUbicaciones
                    puedeVer={ubicaciones.puedeVer}
                    mostrar={ubicaciones.mostrar}
                    onMostrar={ubicaciones.setMostrar}
                    cargando={ubicaciones.cargando}
                    fallo={ubicaciones.fallo}
                    sinCoordenadas={ubicaciones.sinCoordenadas}
                />

                <MapaBase>
                    <EncuadrarEn bounds={bounds} />
                    {zonas.map((zona, indice) => (
                        <Polygon
                            key={zona.id}
                            positions={aLatLngs(zona.geom)}
                            pathOptions={{ color: colorDe(indice), fillOpacity: 0.2, weight: 2 }}
                        >
                            <Tooltip
                                direction="center"
                                permanent={zonas.length <= TOPE_ETIQUETAS_FIJAS}
                                sticky={zonas.length > TOPE_ETIQUETAS_FIJAS}
                            >
                                {zona.nombre}
                            </Tooltip>
                        </Polygon>
                    ))}
                    {ubicaciones.mostrar && (
                        <CapaUbicaciones ubicaciones={ubicaciones.dibujables} />
                    )}
                </MapaBase>
            </Stack>
        </Modal>
    );
}
