import type { QueryClient } from "@tanstack/react-query";
import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";

export type RouterContext = {
    queryClient: QueryClient;
};

// El AppShell vive en _authenticated: /login no va adentro del shell.
export const Route = createRootRouteWithContext<RouterContext>()({
    component: Outlet,
});
