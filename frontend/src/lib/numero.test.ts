import { describe, expect, it } from "vitest";

import { formatearKm2 } from "./numero";

describe("formatearKm2", () => {
    it("formatea el string del Decimal sin decimales", () => {
        expect(formatearKm2("99708.2013")).toBe("99.708");
    });

    it("conserva decimales en una zona chica, que redondeada sería 0", () => {
        expect(formatearKm2("0.4231")).toBe("0,42");
    });

    it("devuelve el vacío para una superficie ausente", () => {
        expect(formatearKm2(null)).toBe("—");
    });

    it("no muestra un 0 falso si la superficie viene vacía", () => {
        // Number("") es 0, no NaN: sin el guard esto pasaría por una superficie real.
        expect(formatearKm2("")).toBe("—");
    });
});
