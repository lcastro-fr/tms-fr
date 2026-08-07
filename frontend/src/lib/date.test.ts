import dayjs from "dayjs";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import { describe, expect, it } from "vitest";

dayjs.extend(utc);
dayjs.extend(timezone);

import {
    aIsoConOffset,
    aWallClock,
    formatearFecha,
    rangoUltimoMes,
} from "./date";

describe("formatearFecha", () => {
    it("muestra el UTC del backend en hora de Buenos Aires", () => {
        expect(formatearFecha("2026-08-06T13:00:00Z")).toBe("06/08/2026 10:00");
    });

    it("respeta el offset que venga, no sólo Z", () => {
        expect(formatearFecha("2026-08-06T13:00:00+00:00")).toBe("06/08/2026 10:00");
    });

    it("devuelve el vacío cuando no hay fecha", () => {
        expect(formatearFecha(null)).toBe("—");
    });
});

describe("aIsoConOffset", () => {
    it("le pone offset explícito al reloj de pared del picker", () => {
        // Un ISO naive es 422 en el backend: este es el punto donde eso se evita.
        expect(aIsoConOffset("2026-08-06 10:00:00")).toBe("2026-08-06T10:00:00-03:00");
    });

    it("interpreta el reloj de pared en TZ_OPERACION, no en la del browser", () => {
        // Con TZ=UTC en el runner, aIsoConOffset no puede devolver +00:00.
        expect(aIsoConOffset("2026-01-15 08:30:00")).toBe("2026-01-15T08:30:00-03:00");
    });

    it("deja pasar el null: fecha_viaje es nullable", () => {
        expect(aIsoConOffset(null)).toBeNull();
    });
});

describe("rangoUltimoMes", () => {
    it("son dos días en el formato que espera el backend", () => {
        const [desde, hasta] = rangoUltimoMes();
        expect(desde).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(hasta).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it("abarca un mes y termina hoy", () => {
        const [desde, hasta] = rangoUltimoMes();
        expect(dayjs(hasta).diff(dayjs(desde), "day")).toBeGreaterThanOrEqual(28);
        expect(dayjs(hasta).diff(dayjs(desde), "day")).toBeLessThanOrEqual(31);
        // El extremo derecho es hoy: si fuera ayer, lo de hoy no se vería al entrar.
        expect(hasta).toBe(dayjs().tz("America/Argentina/Buenos_Aires").format("YYYY-MM-DD"));
    });
});

describe("aWallClock", () => {
    it("es la vuelta de aIsoConOffset", () => {
        const wallClock = "2026-08-06 10:00:00";
        expect(aWallClock(aIsoConOffset(wallClock))).toBe(wallClock);
    });

    it("convierte el UTC del backend antes de dárselo al picker", () => {
        expect(aWallClock("2026-08-06T13:00:00Z")).toBe("2026-08-06 10:00:00");
    });

    it("deja pasar el null", () => {
        expect(aWallClock(null)).toBeNull();
    });
});
