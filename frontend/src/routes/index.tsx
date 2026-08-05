import { Stack, Text, Title } from "@mantine/core";
import { createFileRoute } from "@tanstack/react-router";

function Inicio() {
    return (
        <Stack gap="xs">
            <Title order={2}>Inicio</Title>
            <Text c="dimmed">
                Shell cableado. Todavía no hay pantallas: falta la capa de API.
            </Text>
        </Stack>
    );
}

export const Route = createFileRoute("/")({ component: Inicio });
