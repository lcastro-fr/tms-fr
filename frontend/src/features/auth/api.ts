import { queryOptions } from "@tanstack/react-query";

import { http, setCsrfToken } from "../../api/http";
import type { components } from "../../api/schema";

export type SesionOut = components["schemas"]["SesionOut"];
export type CsrfOut = components["schemas"]["CsrfOut"];
export type LoginIn = components["schemas"]["LoginIn"];
export type PermisoCodigo = components["schemas"]["PermisoCodigo"];

export const authKeys = {
    me: ["auth", "me"] as const,
};

function storeSession(sesion: SesionOut): SesionOut {
    setCsrfToken(sesion.csrf_token);
    return sesion;
}

// staleTime/gcTime explícitos: sin ellos hereda el staleTime: 30_000 global y los
// permisos se revalidarían solos a mitad de sesión.
export const meQueryOptions = () =>
    queryOptions({
        queryKey: authKeys.me,
        queryFn: () => http.get<SesionOut>("/auth/me").then((r) => storeSession(r.data)),
        staleTime: Infinity,
        gcTime: Infinity,
        refetchOnWindowFocus: false,
        retry: false,
    });

// Sólo hace falta estando anónimo: /auth/login y /auth/me ya devuelven el token.
export async function bootstrapCsrf(): Promise<void> {
    const { data } = await http.get<CsrfOut>("/auth/csrf");
    setCsrfToken(data.csrf_token);
}

export async function login(payload: LoginIn): Promise<SesionOut> {
    const { data } = await http.post<SesionOut>("/auth/login", payload);
    return storeSession(data);
}

export async function logout(): Promise<void> {
    await http.post("/auth/logout");
    setCsrfToken(null);
}
