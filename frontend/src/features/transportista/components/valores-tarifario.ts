import { aIsoConOffset, aWallClock } from "../../../lib/date";
import type {
    ModalidadFlete,
    TarifaFleteIn,
    TarifarioDetalleOut,
    TarifarioIn,
    TipoCamion,
} from "../api";

/**
 * El alcance es un campo del formulario y no de la API: `zona_id` y `ubicacion_id` son
 * excluyentes en el backend, y modelarlo como una elección hace que el XOR se cumpla por
 * construcción en vez de depender del validador.
 */
/** `congelada`: una fila ya usada para costear no se edita ni se quita, sólo se agregan nuevas. */
export type FilaFlete = {
    key: string;
    congelada: boolean;
    alcance: "zona" | "ubicacion";
    referencia_id: string | null;
    modalidad: ModalidadFlete;
    tipo_camion: TipoCamion;
    hombreador: boolean;
    precio: string | number;
};

export type FilaConcepto = {
    key: string;
    congelada: boolean;
    concepto_id: string | null;
    precio: string | number;
};

export type Valores = {
    transportista_id: string | null;
    vigente_desde: string | null;
    vigente_hasta: string | null;
    tarifas_flete: FilaFlete[];
    tarifas_concepto: FilaConcepto[];
};

let secuencia = 0;

/** La key de React de una fila: el id del backend no sirve, las nuevas todavía no tienen. */
function nuevaKey(): string {
    secuencia += 1;
    return `fila-${secuencia}`;
}

export function filaFleteVacia(): FilaFlete {
    return {
        key: nuevaKey(),
        congelada: false,
        alcance: "zona",
        referencia_id: null,
        modalidad: "directo",
        tipo_camion: "semi",
        hombreador: false,
        precio: "",
    };
}

export function filaConceptoVacia(): FilaConcepto {
    return { key: nuevaKey(), congelada: false, concepto_id: null, precio: "" };
}

export function valoresIniciales(
    tarifario: TarifarioDetalleOut | null,
    enUso = false,
): Valores {
    if (tarifario === null) {
        return {
            transportista_id: null,
            vigente_desde: null,
            vigente_hasta: null,
            tarifas_flete: [],
            tarifas_concepto: [],
        };
    }
    return {
        transportista_id: String(tarifario.transportista_id),
        vigente_desde: aWallClock(tarifario.vigente_desde),
        vigente_hasta: aWallClock(tarifario.vigente_hasta),
        tarifas_flete: tarifario.tarifas_flete.map((tarifa) => ({
            key: nuevaKey(),
            congelada: enUso,
            alcance: tarifa.zona_id !== null ? "zona" : "ubicacion",
            referencia_id: String(tarifa.zona_id ?? tarifa.ubicacion_id),
            modalidad: tarifa.modalidad as ModalidadFlete,
            tipo_camion: tarifa.tipo_camion as TipoCamion,
            hombreador: tarifa.hombreador,
            precio: tarifa.precio,
        })),
        tarifas_concepto: tarifario.tarifas_concepto.map((tarifa) => ({
            key: nuevaKey(),
            congelada: enUso,
            concepto_id: String(tarifa.concepto_id),
            precio: tarifa.precio,
        })),
    };
}

/** Duplicar arranca del contenido pero sin vigencia: la nueva no puede solaparse con la vieja. */
export function valoresDuplicados(tarifario: TarifarioDetalleOut): Valores {
    return { ...valoresIniciales(tarifario), vigente_desde: null, vigente_hasta: null };
}

function aFleteIn(fila: FilaFlete): TarifaFleteIn {
    const referencia = Number(fila.referencia_id);
    return {
        zona_id: fila.alcance === "zona" ? referencia : null,
        ubicacion_id: fila.alcance === "ubicacion" ? referencia : null,
        modalidad: fila.modalidad,
        tipo_camion: fila.tipo_camion,
        hombreador: fila.hombreador,
        precio: String(fila.precio),
    };
}

export function aPayload(valores: Valores): TarifarioIn {
    return {
        transportista_id: Number(valores.transportista_id),
        // El picker entrega un reloj de pared naive; sin offset el backend responde 422.
        vigente_desde: aIsoConOffset(valores.vigente_desde) as string,
        vigente_hasta: aIsoConOffset(valores.vigente_hasta),
        tarifas_flete: valores.tarifas_flete.map(aFleteIn),
        tarifas_concepto: valores.tarifas_concepto.map((fila) => ({
            concepto_id: Number(fila.concepto_id),
            precio: String(fila.precio),
        })),
    };
}

/** La clave que el backend tiene en una unique parcial: repetirla es un 409. */
export function claveFlete(fila: FilaFlete): string {
    return [fila.alcance, fila.referencia_id, fila.modalidad, fila.tipo_camion, fila.hombreador]
        .map(String)
        .join("|");
}
