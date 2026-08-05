import axios from "axios";

import { toApiError } from "./errors";

export const http = axios.create({
    baseURL: "/api/v1",
    withCredentials: true,
});

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

// Con CSRF_USE_SESSIONS no hay cookie csrftoken que leer: el token llega en el body.
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
    csrfToken = token;
}

http.interceptors.request.use((config) => {
    const method = (config.method ?? "get").toUpperCase();
    if (csrfToken !== null && !SAFE_METHODS.has(method)) {
        config.headers.set("X-CSRFToken", csrfToken);
    }
    return config;
});

type OnUnauthorized = (path: string) => void;

// El redirect lo cablea main.tsx: importar el router acá cierra el ciclo
// router → routes → features → api → router.
let onUnauthorized: OnUnauthorized | null = null;

export function setOnUnauthorized(handler: OnUnauthorized | null): void {
    onUnauthorized = handler;
}

http.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
        const apiError = toApiError(error);
        const isAuthEndpoint = apiError.path.startsWith("/auth/");
        if (apiError.status === 401 && !isAuthEndpoint) {
            setCsrfToken(null);
            onUnauthorized?.(apiError.path);
        }
        return Promise.reject(apiError);
    },
);
