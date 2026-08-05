import { AppShell, Group, Title } from "@mantine/core";
import { Outlet, createRootRoute } from "@tanstack/react-router";

function RootLayout() {
    return (
        <AppShell header={{ height: 56 }} padding="md">
            <AppShell.Header>
                <Group h="100%" px="md" justify="space-between">
                    <Title order={4}>TMS-FR</Title>
                </Group>
            </AppShell.Header>
            <AppShell.Main>
                <Outlet />
            </AppShell.Main>
        </AppShell>
    );
}

export const Route = createRootRoute({ component: RootLayout });
