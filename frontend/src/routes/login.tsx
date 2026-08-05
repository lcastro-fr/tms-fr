import { Card, Center, Stack, Title } from "@mantine/core";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { LoginForm, authKeys, bootstrapCsrf } from "../features/auth";

type LoginSearch = {
    next?: string;
};

function LoginPage() {
    const { next } = Route.useSearch();
    const { queryClient } = Route.useRouteContext();
    const navigate = useNavigate();

    return (
        <Center h="100vh">
            <Card withBorder shadow="sm" padding="xl" w={380}>
                <Stack gap="lg">
                    <Title order={3}>TMS-FR</Title>
                    <LoginForm
                        onSuccess={(sesion) => {
                            queryClient.setQueryData(authKeys.me, sesion);
                            void navigate({ to: next ?? "/" });
                        }}
                    />
                </Stack>
            </Card>
        </Center>
    );
}

export const Route = createFileRoute("/login")({
    validateSearch: (search: Record<string, unknown>): LoginSearch => ({
        next: typeof search.next === "string" ? search.next : undefined,
    }),
    loader: () => bootstrapCsrf(),
    component: LoginPage,
});
