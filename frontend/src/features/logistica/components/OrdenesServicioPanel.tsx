import {
    CloseButton,
    Group,
    Loader,
    Switch,
    Text,
    TextInput,
} from "@mantine/core";
import { DateRangePicker } from "../../../components/DateRangePicker";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
    useMutation,
    useQueryClient,
    useSuspenseQuery,
} from "@tanstack/react-query";
import {
    Suspense,
    lazy,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import type { ApiError } from "../../../api/errors";
import { DataTableExpandible } from "../../../components/DataTableExpandible";
import { formatearPesos } from "../../../lib/money";
import { usePermisos } from "../../auth";
import {
    calcularCostoOrdenServicio,
    opcionesOrdenServicioQueryOptions,
    ordenesServicioKeys,
    ordenesServicioQueryOptions,
} from "../api";
import type { OrdenServicioOut, OrdenesServicioSeleccion } from "../api";
import { ordenesServicioColumns } from "../ordenes-servicio-columns";
import { TicketsDeOrden } from "./TicketsDeOrden";

const OrdenServicioFormModal = lazy(() =>
    import("./OrdenServicioFormModal").then((m) => ({
        default: m.OrdenServicioFormModal,
    })),
);

type Props = {
    filters: OrdenesServicioSeleccion;
    seleccion: OrdenesServicioSeleccion;
    cargando: boolean;
    onFiltersChange: (filters: OrdenesServicioSeleccion) => void;
};

export function OrdenesServicioPanel({
    filters,
    seleccion,
    cargando,
    onFiltersChange,
}: Props) {
    const { can } = usePermisos();
    const queryClient = useQueryClient();
    const { data: ordenes } = useSuspenseQuery(
        ordenesServicioQueryOptions(filters),
    );
    const { data: opciones } = useSuspenseQuery(
        opcionesOrdenServicioQueryOptions(),
    );
    const [editando, setEditando] = useState<OrdenServicioOut | null>(null);

    const calcular = useMutation({
        mutationFn: (orden: OrdenServicioOut) =>
            calcularCostoOrdenServicio(orden.id),
        onSuccess: (costo, orden) => {
            void queryClient.invalidateQueries({
                queryKey: ordenesServicioKeys.all,
            });
            notifications.show({
                color: "green",
                message: `Costo de la OS ${orden.id}: ${formatearPesos(costo.total)}`,
            });
        },
        onError: (error: ApiError, orden) => {
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({
                    queryKey: ordenesServicioKeys.all,
                });
            }
            notifications.show({
                color: "red",
                autoClose: false,
                title: `No se pudo calcular el costo de la OS ${orden.id}`,
                message: error.message,
            });
        },
    });

    const calculandoId = calcular.isPending ? calcular.variables.id : null;

    const etiqueta = useCallback(
        (
            grupo: "tipos_operacion" | "tipos_camion" | "vias",
            value: string | null,
        ) =>
            opciones[grupo].find((o) => o.value === value)?.label ??
            value ??
            "",
        [opciones],
    );

    const columns = useMemo(
        () =>
            ordenesServicioColumns({
                onEditar: setEditando,
                onCalcular: calcular.mutate,
                puedeEditar: can("ordenes_servicio.editar"),
                puedeCalcular: can("ordenes_servicio.calcular_costo"),
                calculandoId,
                etiqueta,
            }),
        [can, calcular.mutate, calculandoId, etiqueta],
    );

    const [busqueda, setBusqueda] = useState(seleccion.numero ?? "");
    const [busquedaDebounced] = useDebouncedValue(busqueda, 300);

    useEffect(() => {
        const normalizada = busquedaDebounced.trim() || undefined;
        if (normalizada !== filters.numero) {
            onFiltersChange({ numero: normalizada });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [busquedaDebounced]);

    const rango: [string | null, string | null] = [
        seleccion.fecha_viaje_desde ?? null,
        seleccion.fecha_viaje_hasta ?? null,
    ];

    return (
        <>
            <Group mb="sm" gap="md" align="flex-end" wrap="wrap">
                <DateRangePicker
                    label="Fecha de viaje"
                    placeholder="Desde – hasta"
                    w={240}
                    valueFormat="DD/MM/YYYY"
                    value={rango}
                    onChange={([desde, hasta]) =>
                        onFiltersChange({
                            fecha_viaje_desde: desde ?? undefined,
                            fecha_viaje_hasta: hasta ?? undefined,
                        })
                    }
                />
                <TextInput
                    label="Buscar"
                    placeholder="Nº de ticket o remito"
                    w={220}
                    value={busqueda}
                    onChange={(event) => setBusqueda(event.currentTarget.value)}
                    rightSection={
                        busqueda ? (
                            <CloseButton
                                size="sm"
                                aria-label="Limpiar la búsqueda"
                                onClick={() => setBusqueda("")}
                            />
                        ) : null
                    }
                />
            </Group>

            <Group justify="space-between" mb="sm">
                <Group gap="lg">
                    <Switch
                        label="Incluir no facturables"
                        checked={seleccion.incluir_no_facturables === true}
                        onChange={(event) =>
                            onFiltersChange({
                                incluir_no_facturables: event.currentTarget
                                    .checked
                                    ? true
                                    : undefined,
                            })
                        }
                    />
                    <Switch
                        label="Sólo sin costo calculado"
                        checked={seleccion.con_costo === false}
                        onChange={(event) =>
                            onFiltersChange({
                                con_costo: event.currentTarget.checked
                                    ? false
                                    : undefined,
                            })
                        }
                    />
                    <Switch
                        label="Incluir sin fecha de viaje"
                        checked={seleccion.incluir_sin_fecha === true}
                        onChange={(event) =>
                            onFiltersChange({
                                incluir_sin_fecha: event.currentTarget.checked
                                    ? true
                                    : undefined,
                            })
                        }
                    />
                    {cargando && <Loader size="xs" />}
                </Group>
            </Group>

            <DataTableExpandible
                columns={columns}
                data={ordenes}
                getRowId={(orden) => String(orden.id)}
                expandido={(orden) => (
                    <TicketsDeOrden tickets={orden.tickets} />
                )}
                puedeExpandir={(orden) => orden.tickets.length > 0}
                vacio="Ninguna orden de servicio coincide con los filtros puestos."
                buscador="Filtrar lo cargado: OS, ticket, origen o transportista"
            />

            <Suspense fallback={<Loader size="sm" />}>
                {editando && (
                    <OrdenServicioFormModal
                        orden={editando}
                        onClose={() => setEditando(null)}
                    />
                )}
            </Suspense>
        </>
    );
}
