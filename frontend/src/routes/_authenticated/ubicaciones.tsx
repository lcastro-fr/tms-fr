import { Stack, Title } from "@mantine/core";
import { createFileRoute, useRouterState } from "@tanstack/react-router";

import { requirePermiso } from "../../features/auth";
import { UbicacionesPanel, ubicacionesQueryOptions } from "../../features/catalog";
import type { UbicacionesSeleccion } from "../../features/catalog";

function booleano(valor: unknown): boolean | undefined {
    return typeof valor === "boolean" ? valor : undefined;
}

function Ubicaciones() {
    const filters = Route.useSearch();
    const navigate = Route.useNavigate();

    const pendientes = useRouterState({
        select: (estado) => estado.location.search as UbicacionesSeleccion,
    });
    const cargando = useRouterState({ select: (estado) => estado.isLoading });

    return (
        <Stack gap="md">
            <Title order={2}>Ubicaciones</Title>
            <UbicacionesPanel
                filters={filters}
                seleccion={pendientes}
                cargando={cargando}
                onFiltersChange={(siguientes) =>
                    void navigate({
                        search: (previo) => ({ ...previo, ...siguientes }),
                        replace: true,
                    })
                }
            />
        </Stack>
    );
}

export const Route = createFileRoute("/_authenticated/ubicaciones")({
    validateSearch: (search: Record<string, unknown>): UbicacionesSeleccion => ({
        validada: booleano(search.validada),
        con_coordenadas: booleano(search.con_coordenadas),
    }),
    loaderDeps: ({ search }) => ({
        validada: search.validada,
        con_coordenadas: search.con_coordenadas,
    }),
    beforeLoad: ({ context }) => requirePermiso(context.sesion, "ubicaciones.ver"),
    loader: ({ context, deps }) =>
        context.queryClient.ensureQueryData(ubicacionesQueryOptions(deps)),
    component: Ubicaciones,
});
