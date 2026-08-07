import { describe, expect, it } from "vitest";

import { formatearPesos } from "./money";

// Intl separa el signo del número con un espacio duro (U+00A0), no con uno común.
const normalizar = (valor: string) => valor.replace(/\s/g, " ");

describe("formatearPesos", () => {
    it("formatea el string del Decimal en pesos", () => {
        expect(normalizar(formatearPesos("185000.00"))).toBe("$ 185.000,00");
    });

    it("conserva los centavos", () => {
        expect(normalizar(formatearPesos("1234.56"))).toBe("$ 1.234,56");
    });

    it("devuelve el vacío para un precio ausente", () => {
        expect(formatearPesos(null)).toBe("—");
    });

    it("no muestra un $ 0,00 falso si el precio viene vacío", () => {
        // Number("") es 0, no NaN: sin el guard esto pasaría por un precio real.
        expect(formatearPesos("")).toBe("—");
    });
});
