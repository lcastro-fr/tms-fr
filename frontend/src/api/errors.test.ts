import { describe, expect, it } from "vitest";

import { ApiError, fieldErrors } from "./errors";

function invalido(errors: unknown): ApiError {
    return new ApiError(422, "payload_invalid", "Payload inválido", { errors }, "/tarifarios/");
}

describe("fieldErrors", () => {
    it("descarta el prefijo del transporte y deja el campo", () => {
        const error = invalido([{ loc: ["body", "payload", "nombre"], msg: "Requerido" }]);

        expect(fieldErrors(error)).toEqual({ nombre: "Requerido" });
    });

    it("arma la ruta con puntos para un item de lista", () => {
        const error = invalido([
            { loc: ["body", "payload", "tarifas_flete", 0, "precio"], msg: "Debe ser >= 0" },
        ]);

        expect(fieldErrors(error)).toEqual({ "tarifas_flete.0.precio": "Debe ser >= 0" });
    });

    it("no colapsa dos filas distintas en el mismo campo", () => {
        const error = invalido([
            { loc: ["body", "payload", "tarifas_flete", 0, "precio"], msg: "primera" },
            { loc: ["body", "payload", "tarifas_flete", 2, "precio"], msg: "tercera" },
        ]);

        expect(fieldErrors(error)).toEqual({
            "tarifas_flete.0.precio": "primera",
            "tarifas_flete.2.precio": "tercera",
        });
    });

    it("mapea el error de fila entera, sin campo final", () => {
        const error = invalido([
            { loc: ["body", "payload", "tarifas_flete", 1], msg: "Elegí una zona o una ubicación" },
        ]);

        expect(fieldErrors(error)).toEqual({
            "tarifas_flete.1": "Elegí una zona o una ubicación",
        });
    });

    it("gana el primer mensaje cuando un campo repite", () => {
        const error = invalido([
            { loc: ["body", "payload", "nombre"], msg: "primero" },
            { loc: ["body", "payload", "nombre"], msg: "segundo" },
        ]);

        expect(fieldErrors(error).nombre).toBe("primero");
    });

    it("business_rule comparte el 422 pero no son errores de campo", () => {
        const error = new ApiError(422, "business_rule", "No se puede", {}, "/tarifarios/");

        expect(fieldErrors(error)).toEqual({});
    });

    it("tolera un detail sin errors y un loc vacío", () => {
        expect(fieldErrors(invalido(undefined))).toEqual({});
        expect(fieldErrors(invalido([{ loc: [], msg: "x" }]))).toEqual({});
        expect(fieldErrors(invalido([{ loc: ["body", "payload"], msg: "x" }]))).toEqual({});
    });
});
