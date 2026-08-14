import { Stack, Title } from "@mantine/core";
import { useDocumentTitle } from "@mantine/hooks";
import { createFileRoute, useRouterState } from "@tanstack/react-router";

import { requirePermiso } from "../../features/auth";
import {
    OrdenesServicioPanel,
    opcionesOrdenServicioQueryOptions,
    ordenesServicioQueryOptions,
} from "../../features/logistica";
import type { OrdenesServicioSeleccion } from "../../features/logistica";
import { rangoUltimoMes } from "../../lib/date";

function booleano(valor: unknown): boolean | undefined {
    return typeof valor === "boolean" ? valor : undefined;
}

// "" fuera del search: ensucia la URL y mintea una entrada de cache aparte.
function texto(valor: unknown): string | undefined {
    return typeof valor === "string" && valor.trim() !== "" ? valor : undefined;
}

function dia(valor: unknown, porDefecto: string): string {
    return typeof valor === "string" && /^\d{4}-\d{2}-\d{2}$/.test(valor)
        ? valor
        : porDefecto;
}

function OrdenesServicio() {
    useDocumentTitle("Órdenes de servicio · Fletes");
    const filters = Route.useSearch();
    const navigate = Route.useNavigate();

    const pendientes = useRouterState({
        select: (estado) => estado.location.search as OrdenesServicioSeleccion,
    });
    const cargando = useRouterState({ select: (estado) => estado.isLoading });

    return (
        <Stack gap="md">
            <Title order={2}>Órdenes de servicio</Title>
            <OrdenesServicioPanel
                filters={filters}
                seleccion={pendientes}
                cargando={cargando}
                onFiltersChange={(next) =>
                    void navigate({
                        search: (prev) => ({ ...prev, ...next }),
                        replace: true,
                    })
                }
            />
        </Stack>
    );
}

export const Route = createFileRoute("/_authenticated/ordenes-servicio")({
    validateSearch: (
        search: Record<string, unknown>,
    ): OrdenesServicioSeleccion => {
        const [desde, hasta] = rangoUltimoMes();
        return {
            incluir_no_facturables: booleano(search.incluir_no_facturables),
            con_costo: booleano(search.con_costo),
            numero: texto(search.numero),
            fecha_viaje_desde: dia(search.fecha_viaje_desde, desde),
            fecha_viaje_hasta: dia(search.fecha_viaje_hasta, hasta),
            incluir_sin_fecha: booleano(search.incluir_sin_fecha),
        };
    },
    loaderDeps: ({ search }) => ({
        incluir_no_facturables: search.incluir_no_facturables,
        con_costo: search.con_costo,
        numero: search.numero,
        fecha_viaje_desde: search.fecha_viaje_desde,
        fecha_viaje_hasta: search.fecha_viaje_hasta,
        incluir_sin_fecha: search.incluir_sin_fecha,
    }),
    beforeLoad: ({ context }) =>
        requirePermiso(context.sesion, "ordenes_servicio.ver"),
    loader: ({ context, deps }) =>
        Promise.all([
            context.queryClient.ensureQueryData(
                ordenesServicioQueryOptions(deps),
            ),
            context.queryClient.ensureQueryData(
                opcionesOrdenServicioQueryOptions(),
            ),
        ]),
    component: OrdenesServicio,
});
