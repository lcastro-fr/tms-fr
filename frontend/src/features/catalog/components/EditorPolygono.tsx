import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";

import * as L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMap } from "react-leaflet";

import { EncuadrarEn } from "../../../components/EncuadrarEn";
import { aLatLngs, boundsDe, cerrarAnillos } from "../../../lib/geojson";
import type { GeoJSONPolygon } from "../api";

// Geoman dispara los eventos de edición sobre la capa y no sobre el mapa. Escucharlos en el
// mapa hace que arrastrar un vértice no llegue nunca al formulario y que el PUT guarde la
// geometría vieja, sin un solo error. Sólo pm:create y pm:remove van en el mapa.
const EVENTOS_DE_EDICION = [
    "pm:update",
    "pm:dragend",
    "pm:markerdragend",
    "pm:vertexadded",
    "pm:vertexremoved",
    "pm:rotateend",
    "pm:cut",
];

type Props = {
    valor: GeoJSONPolygon | null;
    onChange: (geom: GeoJSONPolygon | null) => void;
    onMultiPolygon: () => void;
};

export function EditorPolygono({ valor, onChange, onMultiPolygon }: Props) {
    const map = useMap();
    const capa = useRef<L.Polygon | null>(null);
    // La geometría de arranque se congela: después la manda geoman, no el prop.
    const [inicial] = useState(valor);
    const callbacks = useRef({ onChange, onMultiPolygon });

    useEffect(() => {
        callbacks.current = { onChange, onMultiPolygon };
    }, [onChange, onMultiPolygon]);

    const boundsIniciales = useMemo(() => (inicial ? boundsDe([inicial]) : null), [inicial]);

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
            rotateMode: false,
            // Circle y CircleMarker exportan un Point, y cutPolygon puede partir la zona en
            // un MultiPolygon: el modelo guarda exactamente un Polygon.
            drawMarker: false,
            drawCircle: false,
            drawCircleMarker: false,
            drawPolyline: false,
            drawText: false,
            cutPolygon: false,
        });
        map.pm.setGlobalOptions({ continueDrawing: false, snappable: true, snapDistance: 20 });

        const emitir = () => {
            const actual = capa.current;
            if (!actual) {
                callbacks.current.onChange(null);
                return;
            }
            const feature = actual.toGeoJSON();
            if (feature.geometry.type !== "Polygon") {
                callbacks.current.onMultiPolygon();
                return;
            }
            callbacks.current.onChange({
                type: "Polygon",
                coordinates: cerrarAnillos(feature.geometry.coordinates),
            });
        };

        const escuchar = (poligono: L.Polygon) =>
            EVENTOS_DE_EDICION.forEach((evento) => poligono.on(evento, emitir));
        const dejarDeEscuchar = (poligono: L.Polygon) =>
            EVENTOS_DE_EDICION.forEach((evento) => poligono.off(evento, emitir));

        const usarCapa = (poligono: L.Polygon, emitirAhora: boolean) => {
            const anterior = capa.current;
            if (anterior) {
                // Geoman no tiene modo "una sola figura": la nueva reemplaza a la anterior.
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
            callbacks.current.onChange(null);
        };

        map.on("pm:create", alCrear);
        map.on("pm:remove", alBorrar);

        if (inicial) {
            // El anillo de GeoJSON repite el primer punto al final y Leaflet cierra solo:
            // dejarlo apila dos handles sobre el primer vértice, y arrastrar uno corrompe el
            // anillo sin avisar. La geometría inicial ya está en el form, así que no se emite.
            const anillos = aLatLngs(inicial).map((anillo) => anillo.slice(0, -1));
            usarCapa(L.polygon(anillos).addTo(map), false);
        }

        return () => {
            map.off("pm:create", alCrear);
            map.off("pm:remove", alBorrar);
            map.off("unload", alDescargar);

            const actual = capa.current;
            capa.current = null;
            // MapContainer destruye el mapa en su propio cleanup y React corre el del padre
            // antes que el del hijo, así que acá el mapa ya puede estar muerto. Tocar pm
            // entonces rompe con "Cannot read properties of undefined (reading 'classList')".
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

    return <EncuadrarEn bounds={boundsIniciales} />;
}
