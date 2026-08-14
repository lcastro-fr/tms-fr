import { Button, Group, Loader, Text } from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import {
    useMutation,
    useQueryClient,
    useSuspenseQuery,
} from "@tanstack/react-query";
import type { RowSelectionState } from "@tanstack/react-table";
import { Suspense, lazy, useMemo, useState } from "react";

import type { ApiError } from "../../../api/errors";
import { DataTable } from "../../../components/DataTable";
import { Can, usePermisos } from "../../auth";
import { eliminarZona, zonasKeys, zonasQueryOptions } from "../api";
import type { ZonaOut } from "../api";
import { zonasColumns } from "../zonas-columns";

const ZonaFormModal = lazy(() =>
    import("./ZonaFormModal").then((m) => ({ default: m.ZonaFormModal })),
);
const VisualizarZonasModal = lazy(() =>
    import("./VisualizarZonasModal").then((m) => ({
        default: m.VisualizarZonasModal,
    })),
);

type Editando = ZonaOut | null | undefined;

export function ZonasPanel() {
    const { can } = usePermisos();
    const queryClient = useQueryClient();
    const { data: zonas } = useSuspenseQuery(zonasQueryOptions());

    const [seleccion, setSeleccion] = useState<RowSelectionState>({});
    const [editando, setEditando] = useState<Editando>(undefined);
    const [visualizando, setVisualizando] = useState(false);

    const seleccionadas = useMemo(
        () => zonas.filter((zona) => seleccion[String(zona.id)]),
        [zonas, seleccion],
    );

    const eliminar = useMutation({
        mutationFn: (zona: ZonaOut) => eliminarZona(zona.id),
        onSuccess: (_, zona) => {
            setSeleccion((previa) => {
                const resto = { ...previa };
                delete resto[String(zona.id)];
                return resto;
            });
            void queryClient.invalidateQueries({ queryKey: zonasKeys.all });
            notifications.show({
                color: "green",
                message: `Se dio de baja la zona ${zona.nombre}`,
            });
        },
        onError: (error: ApiError) => {
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({ queryKey: zonasKeys.all });
            }
            notifications.show({
                color: "red",
                title:
                    error.code === "conflict"
                        ? "La zona está en uso"
                        : "No se pudo eliminar",
                message: error.message,
            });
        },
    });

    const confirmarBaja = (zona: ZonaOut) =>
        modals.openConfirmModal({
            title: "Eliminar la zona",
            children: (
                <Text size="sm">
                    Esta seguro de eliminar la zona {zona.nombre} ?
                </Text>
            ),
            labels: { confirm: "Eliminar", cancel: "Cancelar" },
            confirmProps: { color: "red" },
            onConfirm: () => eliminar.mutate(zona),
        });

    const columns = useMemo(
        () =>
            zonasColumns({
                onEditar: setEditando,
                onEliminar: confirmarBaja,
                puedeEditar: can("zonas.editar"),
                puedeEliminar: can("zonas.eliminar"),
            }),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [can],
    );

    return (
        <>
            <Group justify="space-between" mb="sm">
                <Button
                    disabled={seleccionadas.length === 0}
                    onClick={() => setVisualizando(true)}
                >
                    Visualizar
                    {seleccionadas.length > 0
                        ? ` (${seleccionadas.length})`
                        : ""}
                </Button>
                <Can permiso="zonas.crear">
                    <Button onClick={() => setEditando(null)}>
                        Nueva zona
                    </Button>
                </Can>
            </Group>

            <DataTable
                columns={columns}
                data={zonas}
                getRowId={(zona) => String(zona.id)}
                rowSelection={seleccion}
                onRowSelectionChange={setSeleccion}
                vacio="Todavía no hay zonas cargadas."
                buscador="Nombre"
            />

            <Suspense fallback={<Loader size="sm" />}>
                {editando !== undefined && (
                    <ZonaFormModal
                        zona={editando}
                        onClose={() => setEditando(undefined)}
                    />
                )}
                {visualizando && seleccionadas.length > 0 && (
                    <VisualizarZonasModal
                        zonas={seleccionadas}
                        onClose={() => setVisualizando(false)}
                    />
                )}
            </Suspense>
        </>
    );
}
