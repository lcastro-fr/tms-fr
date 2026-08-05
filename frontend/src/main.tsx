import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";

import { Providers } from "./app/providers";
import { router } from "./app/router";

const rootElement = document.getElementById("root");

if (!rootElement) {
    throw new Error("No se encontró el elemento #root");
}

createRoot(rootElement).render(
    <StrictMode>
        <Providers>
            <RouterProvider router={router} />
        </Providers>
    </StrictMode>,
);
