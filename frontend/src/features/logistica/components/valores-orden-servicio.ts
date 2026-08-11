import { aIsoConOffset, aWallClock } from "../../../lib/date";
import type {
    OrdenServicioDestinoOut,
    OrdenServicioDetalleOut,
    OrdenServicioIn,
} from "../api";

export type FilaDestino = {
    key: string;
    ubicacion_id: string | null;
};

export type Valores = {
    fecha_viaje: string | null;
    tipo_operacion: OrdenServicioIn["tipo_operacion"];
    tipo_camion: OrdenServicioIn["tipo_camion"];
    via: OrdenServicioIn["via"];
    modalidad: OrdenServicioIn["modalidad"];
    hombreador: boolean;
    facturable: boolean;
    destinos: FilaDestino[];
};

let secuencia = 0;

/** La key de React de una fila: el id del backend no sirve, las nuevas todavía no tienen. */
function nuevaKey(): string {
    secuencia += 1;
    return `destino-${secuencia}`;
}

export function filaDestinoVacia(): FilaDestino {
    return { key: nuevaKey(), ubicacion_id: null };
}

export function aFilasDestino(destinos: OrdenServicioDestinoOut[]): FilaDestino[] {
    return destinos.map((destino) => ({
        key: nuevaKey(),
        ubicacion_id: String(destino.ubicacion_id),
    }));
}

export function valoresIniciales(detalle: OrdenServicioDetalleOut): Valores {
    return {
        fecha_viaje: aWallClock(detalle.fecha_viaje),
        tipo_operacion: detalle.tipo_operacion as Valores["tipo_operacion"],
        tipo_camion: (detalle.tipo_camion as Valores["tipo_camion"]) ?? null,
        via: detalle.via as Valores["via"],
        modalidad: (detalle.modalidad as Valores["modalidad"]) ?? null,
        hombreador: detalle.hombreador,
        facturable: detalle.facturable,
        destinos: aFilasDestino(detalle.destinos),
    };
}

export function aPayload(valores: Valores): OrdenServicioIn {
    return {
        fecha_viaje: aIsoConOffset(valores.fecha_viaje),
        tipo_operacion: valores.tipo_operacion,
        tipo_camion: valores.tipo_camion,
        via: valores.via,
        modalidad: valores.modalidad,
        hombreador: valores.hombreador,
        facturable: valores.facturable,
        // Siempre se mandan: [] borra, omitirlos sería "no tocar".
        destinos: valores.destinos
            .filter((fila) => fila.ubicacion_id !== null)
            .map((fila) => ({ ubicacion_id: Number(fila.ubicacion_id) })),
    };
}
