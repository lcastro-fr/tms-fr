import { Code, List, Stack, Text, Title } from "@mantine/core";
import { createFileRoute } from "@tanstack/react-router";

import { usePermisos } from "../../features/auth";

function Inicio() {
    const { sesion } = usePermisos();

    return (
        <Stack gap="xs">
            <Title order={2}>Inicio</Title>
            <Text c="dimmed">
                Sesión de {sesion.email}. Roles: {sesion.roles.join(", ") || "ninguno"}.
            </Text>
            <List size="sm">
                {sesion.permisos.map((permiso) => (
                    <List.Item key={permiso}>
                        <Code>{permiso}</Code>
                    </List.Item>
                ))}
            </List>
        </Stack>
    );
}

export const Route = createFileRoute("/_authenticated/")({ component: Inicio });
