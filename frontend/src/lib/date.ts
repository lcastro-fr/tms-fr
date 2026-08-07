import dayjs from "dayjs";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";

dayjs.extend(utc);
dayjs.extend(timezone);

export const TZ_OPERACION = "America/Argentina/Buenos_Aires";

/** El formato naive que usan los pickers de @mantine/dates. */
const WALL_CLOCK = "YYYY-MM-DD HH:mm:ss";

export function formatearFecha(iso: string | null, vacio = "—"): string {
    if (!iso) {
        return vacio;
    }
    return dayjs(iso).tz(TZ_OPERACION).format("DD/MM/YYYY HH:mm");
}

/** Del ISO del backend al string naive que espera el picker. */
export function aWallClock(iso: string | null): string | null {
    return iso ? dayjs(iso).tz(TZ_OPERACION).format(WALL_CLOCK) : null;
}

/**
 * Del string naive del picker al ISO que exige el backend. Un ISO sin offset es 422:
 * el reloj de pared que eligió el usuario se interpreta en TZ_OPERACION, no en la del browser.
 */
export function aIsoConOffset(wallClock: string | null): string | null {
    return wallClock ? dayjs.tz(wallClock, TZ_OPERACION).format() : null;
}

/** El día de hoy en la zona de la operación, no en la del browser. */
const DIA = "YYYY-MM-DD";

/**
 * Los últimos 30 días corridos, hasta hoy inclusive. Es el rango con el que arranca la
 * pantalla de órdenes de servicio.
 */
export function rangoUltimoMes(): [string, string] {
    const hoy = dayjs().tz(TZ_OPERACION);
    return [hoy.subtract(1, "month").format(DIA), hoy.format(DIA)];
}
