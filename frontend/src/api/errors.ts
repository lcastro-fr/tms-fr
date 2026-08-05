import { AxiosError } from "axios";

export type ApiErrorCode =
    | "domain_error"
    | "unauthorized"
    | "forbidden"
    | "not_found"
    | "conflict"
    | "business_rule"
    | "payload_invalid"
    | "http_error"
    | "internal_error"
    | "network_error";

export class ApiError extends Error {
    readonly status: number;
    readonly code: ApiErrorCode;
    readonly detail: Record<string, unknown>;
    readonly path: string;

    constructor(
        status: number,
        code: ApiErrorCode,
        message: string,
        detail: Record<string, unknown>,
        path: string,
    ) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
        this.detail = detail;
        this.path = path;
    }
}

type ErrorEnvelope = {
    error: { code: string; message: string; detail?: Record<string, unknown> };
};

function isEnvelope(data: unknown): data is ErrorEnvelope {
    if (typeof data !== "object" || data === null || !("error" in data)) {
        return false;
    }
    const { error } = data as { error: unknown };
    return (
        typeof error === "object" &&
        error !== null &&
        "code" in error &&
        typeof (error as { code: unknown }).code === "string"
    );
}

export function toApiError(error: unknown): ApiError {
    if (error instanceof ApiError) {
        return error;
    }

    const axiosError = error as AxiosError;
    const path = axiosError.config?.url ?? "";

    // Red caída, o request cancelada por el router.
    if (!axiosError.response) {
        return new ApiError(
            0,
            "network_error",
            axiosError.message || "No se pudo contactar al servidor.",
            {},
            path,
        );
    }

    const { status, data } = axiosError.response;

    // Con DEBUG=True el handler de 500 re-lanza y Django devuelve HTML.
    if (!isEnvelope(data)) {
        return new ApiError(
            status,
            "internal_error",
            `El servidor respondió ${status} sin el envelope de error.`,
            {},
            path,
        );
    }

    return new ApiError(
        status,
        data.error.code as ApiErrorCode,
        data.error.message,
        data.error.detail ?? {},
        path,
    );
}

type PydanticError = { loc: (string | number)[]; msg: string };

/** Sólo para payload_invalid: business_rule comparte el 422 pero no son errores de campo. */
export function fieldErrors(error: ApiError): Record<string, string> {
    if (error.code !== "payload_invalid") {
        return {};
    }

    const errors = error.detail.errors;
    if (!Array.isArray(errors)) {
        return {};
    }

    const result: Record<string, string> = {};
    for (const item of errors as PydanticError[]) {
        // loc llega como ["body", "payload", "nombre"]: el campo es lo último.
        const field = item.loc?.at(-1);
        if (typeof field === "string" && !(field in result)) {
            result[field] = item.msg;
        }
    }
    return result;
}
