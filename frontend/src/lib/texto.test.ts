import { describe, expect, it } from "vitest";

import { normalizarTexto } from "./texto";

describe("normalizarTexto", () => {
    it("saca los acentos y baja a minúsculas", () => {
        expect(normalizarTexto("Córdoba")).toBe("cordoba");
        expect(normalizarTexto("TUCUMÁN")).toBe("tucuman");
    });

    it("saca la diéresis", () => {
        expect(normalizarTexto("Güemes")).toBe("guemes");
    });

    it("convierte la ñ en n", () => {
        // Es a propósito: nadie tipea "ñ" para buscar "Ñandú".
        expect(normalizarTexto("Ñandú")).toBe("nandu");
    });

    it("tolera el string vacío", () => {
        expect(normalizarTexto("")).toBe("");
    });
});
