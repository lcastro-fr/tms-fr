import type { ReactNode } from "react";

import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClientProvider } from "@tanstack/react-query";

import { queryClient } from "./query-client";
import { theme } from "./theme";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <QueryClientProvider client={queryClient}>
            <MantineProvider theme={theme} defaultColorScheme="auto">
                <ModalsProvider>
                    {children}
                    <Notifications />
                </ModalsProvider>
            </MantineProvider>
        </QueryClientProvider>
    );
}
