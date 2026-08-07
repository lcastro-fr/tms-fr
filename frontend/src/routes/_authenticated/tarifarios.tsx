import { Stack, Title } from "@mantine/core";
import { createFileRoute, useRouterState } from "@tanstack/react-router";

import { requirePermiso } from "../../features/auth";
import {
    TarifariosPanel,
    tarifarioOpcionesQueryOptions,
    tarifariosQueryOptions,
} from "../../features/transportista";
import type { TarifariosSeleccion } from "../../features/transportista";

function booleano(valor: unknown): boolean | undefined {
    return typeof valor === "boolean" ? valor : undefined;
}

function entero(valor: unknown): number | undefined {
    return typeof valor === "number" && Number.isInteger(valor) ? valor : undefined;
}

function Tarifarios() {
    const filters = Route.useSearch();
    const navigate = Route.useNavigate();

    const pendientes = useRouterState({
        select: (estado) => estado.location.search as TarifariosSeleccion,
    });
    const cargando = useRouterState({ select: (estado) => estado.isLoading });

    return (
        <Stack gap="md">
            <Title order={2}>Tarifarios</Title>
            <TarifariosPanel
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

export const Route = createFileRoute("/_authenticated/tarifarios")({
    validateSearch: (search: Record<string, unknown>): TarifariosSeleccion => ({
        transportista_id: entero(search.transportista_id),
        incluir_historicos: booleano(search.incluir_historicos),
    }),
    loaderDeps: ({ search }) => ({
        transportista_id: search.transportista_id,
        incluir_historicos: search.incluir_historicos,
    }),
    beforeLoad: ({ context }) => requirePermiso(context.sesion, "tarifarios.ver"),
    loader: ({ context, deps }) =>
        Promise.all([
            context.queryClient.ensureQueryData(tarifariosQueryOptions(deps)),
            context.queryClient.ensureQueryData(tarifarioOpcionesQueryOptions()),
        ]),
    component: Tarifarios,
});
