import { Stack, Title } from "@mantine/core";
import { createFileRoute } from "@tanstack/react-router";

import { requirePermiso } from "../../features/auth";
import { ZonasPanel, zonasQueryOptions } from "../../features/catalog";

function Zonas() {
    return (
        <Stack gap="md">
            <Title order={2}>Zonas</Title>
            <ZonasPanel />
        </Stack>
    );
}

export const Route = createFileRoute("/_authenticated/zonas")({
    beforeLoad: ({ context }) => requirePermiso(context.sesion, "zonas.ver"),
    loader: ({ context }) => context.queryClient.ensureQueryData(zonasQueryOptions()),
    component: Zonas,
});
