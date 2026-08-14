import { describe, expect, it } from "vitest";

import { diferenciaPesos, formatearPesos } from "./money";

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

describe("diferenciaPesos", () => {
    it("marca con + lo que se pagó de más", () => {
        expect(normalizar(diferenciaPesos("190000.00", "185000.00") ?? "")).toBe(
            "+$ 5.000,00",
        );
    });

    it("marca con - lo que se pagó de menos", () => {
        expect(normalizar(diferenciaPesos("180000.00", "185000.00") ?? "")).toBe(
            "-$ 5.000,00",
        );
    });

    it("no devuelve nada cuando los dos importes coinciden", () => {
        expect(diferenciaPesos("185000.00", "185000.00")).toBeNull();
    });

    it("no arrastra la cola binaria de la resta en float", () => {
        // 0.1 + 0.2 !== 0.3: sin el redondeo esto daría un desvío de 1e-10 en pantalla.
        expect(diferenciaPesos("0.30", "0.10")).not.toBeNull();
        expect(diferenciaPesos("1000.30", "1000.30")).toBeNull();
    });

    it("no devuelve nada si falta alguno de los dos", () => {
        expect(diferenciaPesos(null, "185000.00")).toBeNull();
        expect(diferenciaPesos("185000.00", null)).toBeNull();
        expect(diferenciaPesos("", "185000.00")).toBeNull();
    });
});
