import { Button, Group, Loader, Select, Switch, Text } from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Suspense, lazy, useMemo, useState } from "react";

import type { ApiError } from "../../../api/errors";
import { DataTable } from "../../../components/DataTable";
import { Can, usePermisos } from "../../auth";
import {
    eliminarTarifario,
    tarifarioOpcionesQueryOptions,
    tarifariosKeys,
    tarifariosQueryOptions,
} from "../api";
import type { TarifarioOut, TarifariosSeleccion } from "../api";
import { tarifariosColumns } from "../tarifarios-columns";
import type { Modo } from "./TarifarioFormModal";

const TarifarioFormModal = lazy(() =>
    import("./TarifarioFormModal").then((m) => ({ default: m.TarifarioFormModal })),
);
const CerrarVigenciaModal = lazy(() =>
    import("./CerrarVigenciaModal").then((m) => ({ default: m.CerrarVigenciaModal })),
);

type Props = {
    filters: TarifariosSeleccion;
    seleccion: TarifariosSeleccion;
    cargando: boolean;
    onFiltersChange: (filters: TarifariosSeleccion) => void;
};

type Editando = { tarifarioId: number | null; modo: Modo };

export function TarifariosPanel({ filters, seleccion, cargando, onFiltersChange }: Props) {
    const { can } = usePermisos();
    const queryClient = useQueryClient();
    const { data: tarifarios } = useSuspenseQuery(tarifariosQueryOptions(filters));
    const { data: opciones } = useSuspenseQuery(tarifarioOpcionesQueryOptions());

    const [editando, setEditando] = useState<Editando | null>(null);
    const [cerrando, setCerrando] = useState<TarifarioOut | null>(null);

    const eliminar = useMutation({
        mutationFn: (tarifario: TarifarioOut) => eliminarTarifario(tarifario.id),
        onSuccess: (_, tarifario) => {
            void queryClient.invalidateQueries({ queryKey: tarifariosKeys.all });
            notifications.show({
                color: "green",
                message: `Se dio de baja el tarifario de ${tarifario.transportista_razon_social}`,
            });
        },
        onError: (error: ApiError) => {
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({ queryKey: tarifariosKeys.all });
            }
            notifications.show({
                color: "red",
                title:
                    error.code === "conflict"
                        ? "El tarifario está en uso"
                        : "No se pudo dar de baja",
                message: error.message,
            });
        },
    });

    const confirmarBaja = (tarifario: TarifarioOut) =>
        modals.openConfirmModal({
            title: "Dar de baja el tarifario",
            children: (
                <Text size="sm">
                    Se dan de baja también sus {tarifario.cantidad_fletes} tarifas de flete y sus{" "}
                    {tarifario.cantidad_conceptos} conceptos. ¿Confirmás?
                </Text>
            ),
            labels: { confirm: "Dar de baja", cancel: "Cancelar" },
            confirmProps: { color: "red" },
            onConfirm: () => eliminar.mutate(tarifario),
        });

    const columns = useMemo(
        () =>
            tarifariosColumns({
                onAbrir: (tarifario) =>
                    setEditando({ tarifarioId: tarifario.id, modo: "edicion" }),
                onDuplicar: (tarifario) =>
                    setEditando({ tarifarioId: tarifario.id, modo: "duplicado" }),
                onCerrar: setCerrando,
                onEliminar: confirmarBaja,
                puedeEditar: can("tarifarios.editar"),
                puedeCrear: can("tarifarios.crear"),
                puedeEliminar: can("tarifarios.eliminar"),
            }),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [can],
    );

    const transportistas = opciones.transportistas.map((t) => ({
        value: String(t.id),
        label: t.razon_social,
    }));

    return (
        <>
            <Group justify="space-between" mb="sm">
                <Group gap="lg">
                    <Select
                        aria-label="Filtrar por transportista"
                        placeholder="Todos los transportistas"
                        searchable
                        clearable
                        data={transportistas}
                        value={
                            seleccion.transportista_id ? String(seleccion.transportista_id) : null
                        }
                        onChange={(valor) =>
                            onFiltersChange({
                                transportista_id: valor ? Number(valor) : undefined,
                            })
                        }
                    />
                    {/* El default filtra a los vigentes, así que el control se nombra por lo
                        que agrega y no por lo que restringe. */}
                    <Switch
                        label="Incluir históricos"
                        checked={seleccion.incluir_historicos === true}
                        onChange={(event) =>
                            onFiltersChange({
                                incluir_historicos: event.currentTarget.checked ? true : undefined,
                            })
                        }
                    />
                    {cargando && <Loader size="xs" />}
                </Group>
                <Can permiso="tarifarios.crear">
                    <Button onClick={() => setEditando({ tarifarioId: null, modo: "alta" })}>
                        Nuevo tarifario
                    </Button>
                </Can>
            </Group>

            <DataTable
                columns={columns}
                data={tarifarios}
                getRowId={(tarifario) => String(tarifario.id)}
                vacio="Todavía no hay tarifarios cargados."
            />

            <Suspense fallback={<Loader size="sm" />}>
                {editando !== null && (
                    <TarifarioFormModal
                        tarifarioId={editando.tarifarioId}
                        modo={editando.modo}
                        onClose={() => setEditando(null)}
                    />
                )}
                {cerrando !== null && (
                    <CerrarVigenciaModal
                        tarifario={cerrando}
                        onClose={() => setCerrando(null)}
                    />
                )}
            </Suspense>
        </>
    );
}
