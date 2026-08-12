import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";

import * as L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMap } from "react-leaflet";

import { EncuadrarEn } from "../../../components/EncuadrarEn";
import { aLatLngs, boundsDe, cerrarAnillos } from "../../../lib/geojson";
import type { Bounds } from "../../../lib/geojson";
import type { GeoJSONMultiPolygon } from "../api";

const EVENTOS_DE_EDICION = [
    "pm:update",
    "pm:dragend",
    "pm:markerdragend",
    "pm:vertexadded",
    "pm:vertexremoved",
    "pm:rotateend",
    "pm:cut",
];

/** La geometría compuesta por el selector de divisiones. `version` es lo que dispara el reemplazo. */
export type Semilla = { geom: GeoJSONMultiPolygon; version: number };

type Props = {
    valor: GeoJSONMultiPolygon | null;
    semilla?: Semilla | null;
    onChange: (geom: GeoJSONMultiPolygon | null) => void;
};

function sinVerticeDeCierre(geom: GeoJSONMultiPolygon) {
    return aLatLngs(geom).map((poligono) =>
        poligono.map((anillo) => anillo.slice(0, -1)),
    );
}

export function EditorPolygono({ valor, semilla, onChange }: Props) {
    const map = useMap();
    const capa = useRef<L.Polygon | null>(null);
    const [inicial] = useState(valor);
    const onChangeRef = useRef(onChange);
    const reemplazar = useRef<((geom: GeoJSONMultiPolygon) => void) | null>(
        null,
    );

    const boundsIniciales = useMemo(
        () => (inicial ? boundsDe([inicial]) : null),
        [inicial],
    );
    const bounds = useMemo<Bounds | null>(
        () => (semilla ? boundsDe([semilla.geom]) : boundsIniciales),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [semilla?.version, boundsIniciales],
    );

    useEffect(() => {
        onChangeRef.current = onChange;
    }, [onChange]);

    useEffect(() => {
        let vivo = true;
        const alDescargar = () => {
            vivo = false;
        };
        map.on("unload", alDescargar);

        map.pm.addControls({
            position: "topleft",
            drawPolygon: true,
            drawRectangle: true,
            editMode: true,
            dragMode: true,
            removalMode: true,
            cutPolygon: true,
            rotateMode: false,
            drawMarker: false,
            drawCircle: false,
            drawCircleMarker: false,
            drawPolyline: false,
            drawText: false,
        });
        map.pm.setGlobalOptions({
            continueDrawing: false,
            snappable: true,
            snapDistance: 20,
        });

        const emitir = () => {
            const actual = capa.current;
            if (!actual) {
                onChangeRef.current(null);
                return;
            }
            const { geometry } = actual.toGeoJSON();
            const coordinates =
                geometry.type === "Polygon"
                    ? [geometry.coordinates]
                    : geometry.type === "MultiPolygon"
                      ? geometry.coordinates
                      : null;
            if (!coordinates) {
                onChangeRef.current(null);
                return;
            }
            onChangeRef.current({
                type: "MultiPolygon",
                coordinates: cerrarAnillos(coordinates),
            });
        };

        const escuchar = (poligono: L.Polygon) =>
            EVENTOS_DE_EDICION.forEach((evento) => poligono.on(evento, emitir));
        const dejarDeEscuchar = (poligono: L.Polygon) =>
            EVENTOS_DE_EDICION.forEach((evento) =>
                poligono.off(evento, emitir),
            );

        const usarCapa = (poligono: L.Polygon, emitirAhora: boolean) => {
            const anterior = capa.current;
            if (anterior) {
                dejarDeEscuchar(anterior);
                anterior.remove();
            }
            capa.current = poligono;
            escuchar(poligono);
            if (emitirAhora) {
                emitir();
            }
        };

        const alCrear = (evento: { layer: L.Layer }) =>
            usarCapa(evento.layer as L.Polygon, true);

        const alBorrar = (evento: { layer: L.Layer }) => {
            if (evento.layer !== capa.current) {
                return;
            }
            dejarDeEscuchar(evento.layer as L.Polygon);
            capa.current = null;
            onChangeRef.current(null);
        };

        map.on("pm:create", alCrear);
        map.on("pm:remove", alBorrar);

        reemplazar.current = (geom) =>
            usarCapa(L.polygon(sinVerticeDeCierre(geom)).addTo(map), true);

        if (inicial) {
            usarCapa(L.polygon(sinVerticeDeCierre(inicial)).addTo(map), false);
        }

        return () => {
            reemplazar.current = null;
            map.off("pm:create", alCrear);
            map.off("pm:remove", alBorrar);
            map.off("unload", alDescargar);

            const actual = capa.current;
            capa.current = null;
            if (!vivo) {
                return;
            }
            if (actual) {
                dejarDeEscuchar(actual);
                actual.remove();
            }
            map.pm.removeControls();
        };
    }, [map, inicial]);

    useEffect(() => {
        if (semilla) {
            reemplazar.current?.(semilla.geom);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [semilla?.version]);

    return <EncuadrarEn bounds={bounds} />;
}
