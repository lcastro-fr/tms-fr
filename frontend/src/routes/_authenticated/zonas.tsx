import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { createFileRoute } from "@tanstack/react-router";

import { Can, requirePermiso } from "../../features/auth";

function Zonas() {
    return (
        <Stack gap="xs">
            <Group justify="space-between">
                <Title order={2}>Zonas</Title>
                <Can permiso="zonas.crear">
                    <Button>Nueva zona</Button>
                </Can>
            </Group>
            <Text c="dimmed">
                La pantalla todavía no está construida. Esta ruta existe para ejercitar el
                guard por permiso y el filtrado de la navbar.
            </Text>
        </Stack>
    );
}

export const Route = createFileRoute("/_authenticated/zonas")({
    beforeLoad: ({ context }) => requirePermiso(context.sesion, "zonas.ver"),
    component: Zonas,
});
