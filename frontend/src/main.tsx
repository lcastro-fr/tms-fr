import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";

import { setOnUnauthorized } from "./api/http";
import { Providers } from "./app/providers";
import { queryClient } from "./app/query-client";
import { router } from "./app/router";

const rootElement = document.getElementById("root");

if (!rootElement) {
    throw new Error("No se encontró el elemento #root");
}

setOnUnauthorized(() => {
    queryClient.clear();
    void router.navigate({
        to: "/login",
        search: { next: router.state.location.href },
    });
});

createRoot(rootElement).render(
    <StrictMode>
        <Providers>
            <RouterProvider router={router} />
        </Providers>
    </StrictMode>,
);
