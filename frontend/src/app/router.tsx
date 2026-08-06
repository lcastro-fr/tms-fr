import { Center, Loader } from "@mantine/core";
import { createRouter } from "@tanstack/react-router";

import { routeTree } from "../routeTree.gen";
import { queryClient } from "./query-client";

export const router = createRouter({
    routeTree,
    context: { queryClient },
    defaultPendingComponent: () => (
        <Center h="8rem">
            <Loader size="sm" />
        </Center>
    ),
});

declare module "@tanstack/react-router" {
    interface Register {
        router: typeof router;
    }
}
