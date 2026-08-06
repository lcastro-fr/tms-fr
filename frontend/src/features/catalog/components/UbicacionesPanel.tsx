import { Group, Loader, Switch, Text } from "@mantine/core";
import { useSuspenseQuery } from "@tanstack/react-query";
import { Suspense, lazy, useMemo, useState } from "react";

import { DataTable } from "../../../components/DataTable";
import { usePermisos } from "../../auth";
import { ubicacionesQueryOptions } from "../api";
import type { UbicacionOut, UbicacionesSeleccion } from "../api";
import { ubicacionesColumns } from "../ubicaciones-columns";

const UbicacionFormModal = lazy(() =>
    import("./UbicacionFormModal").then((m) => ({ default: m.UbicacionFormModal })),
);

type Props = {
    filters: UbicacionesSeleccion;
    seleccion: UbicacionesSeleccion;
    cargando: boolean;
    onFiltersChange: (filters: UbicacionesSeleccion) => void;
};

export function UbicacionesPanel({ filters, seleccion, cargando, onFiltersChange }: Props) {
    const { can } = usePermisos();
    const { data: ubicaciones } = useSuspenseQuery(ubicacionesQueryOptions(filters));
    const [editando, setEditando] = useState<UbicacionOut | null>(null);

    const sinCoordenadas = useMemo(
        () => ubicaciones.filter((u) => u.coordinates === null).length,
        [ubicaciones],
    );

    const columns = useMemo(
        () =>
            ubicacionesColumns({
                onEditar: setEditando,
                puedeEditar: can("ubicaciones.editar"),
            }),
        [can],
    );

    return (
        <>
            <Group justify="space-between" mb="sm">
                <Group gap="lg">
                    <Switch
                        label="Sólo pendientes de validar"
                        checked={seleccion.validada === false}
                        onChange={(event) =>
                            onFiltersChange({
                                validada: event.currentTarget.checked ? false : undefined,
                            })
                        }
                    />
                    <Switch
                        label="Sólo sin coordenada"
                        checked={seleccion.con_coordenadas === false}
                        onChange={(event) =>
                            onFiltersChange({
                                con_coordenadas: event.currentTarget.checked ? false : undefined,
                            })
                        }
                    />
                    {cargando && <Loader size="xs" />}
                </Group>
                <Text c="dimmed" size="sm">
                    {ubicaciones.length} ubicaciones
                    {sinCoordenadas > 0 && `, ${sinCoordenadas} sin coordenada`}
                </Text>
            </Group>

            <DataTable
                columns={columns}
                data={ubicaciones}
                getRowId={(ubicacion) => String(ubicacion.id)}
                vacio={
                    filters.validada === false || filters.con_coordenadas === false
                        ? "No queda ninguna ubicación en ese estado."
                        : "Todavía no hay ubicaciones cargadas."
                }
            />

            <Suspense fallback={<Loader size="sm" />}>
                {editando && (
                    <UbicacionFormModal
                        ubicacion={editando}
                        onClose={() => setEditando(null)}
                    />
                )}
            </Suspense>
        </>
    );
}
