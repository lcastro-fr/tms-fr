import {
    Alert,
    Badge,
    Button,
    Checkbox,
    Fieldset,
    Group,
    Modal,
    Select,
    SimpleGrid,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
    useMutation,
    useQueryClient,
    useSuspenseQuery,
} from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, fieldErrors } from "../../../api/errors";
import { aIsoConOffset, aWallClock, formatearFecha } from "../../../lib/date";
import { formatearPesos } from "../../../lib/money";
import { Can, usePermisos } from "../../auth";
import {
    actualizarOrdenServicio,
    calcularCostoOrdenServicio,
    opcionesOrdenServicioQueryOptions,
    ordenServicioQueryOptions,
    ordenesServicioKeys,
} from "../api";
import type {
    CostoOrdenServicioOut,
    OrdenServicioIn,
    OrdenServicioOut,
    RemitoOut,
} from "../api";
import { TicketsDeOrden } from "./TicketsDeOrden";

type Props = {
    orden: OrdenServicioOut;
    onClose: () => void;
};

type Valores = {
    fecha_viaje: string | null;
    tipo_operacion: OrdenServicioIn["tipo_operacion"];
    tipo_camion: OrdenServicioIn["tipo_camion"];
    via: OrdenServicioIn["via"];
    hombreador: boolean;
    facturable: boolean;
};

export function OrdenServicioFormModal({ orden, onClose }: Props) {
    const queryClient = useQueryClient();
    const { can } = usePermisos();
    const puedeEditar = can("ordenes_servicio.editar");
    const { data: opciones } = useSuspenseQuery(
        opcionesOrdenServicioQueryOptions(),
    );
    // El detalle es lo que trae tickets y remitos; la fila de la lista no los tiene todos.
    const { data: detalle } = useSuspenseQuery(
        ordenServicioQueryOptions(orden.id),
    );
    const [costo, setCosto] = useState<CostoOrdenServicioOut | null>(
        detalle.costo ?? null,
    );

    const form = useForm<Valores>({
        initialValues: {
            fecha_viaje: aWallClock(detalle.fecha_viaje),
            tipo_operacion: detalle.tipo_operacion as Valores["tipo_operacion"],
            tipo_camion:
                (detalle.tipo_camion as Valores["tipo_camion"]) ?? null,
            via: detalle.via as Valores["via"],
            hombreador: detalle.hombreador,
            facturable: detalle.facturable,
        },
    });

    const guardar = useMutation({
        mutationFn: (valores: Valores) => {
            const payload: OrdenServicioIn = {
                ...valores,
                fecha_viaje: aIsoConOffset(valores.fecha_viaje),
            };
            return actualizarOrdenServicio(orden.id, payload);
        },
        onSuccess: (guardada) => {
            void queryClient.invalidateQueries({
                queryKey: ordenesServicioKeys.all,
            });
            notifications.show({
                color: "green",
                message: `Se guardó la OS ${guardada.id}`,
            });
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
            if (error.code === "business_rule" || error.code === "conflict") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({
                    queryKey: ordenesServicioKeys.all,
                });
                onClose();
                return;
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const calcular = useMutation({
        mutationFn: () => calcularCostoOrdenServicio(orden.id),
        onSuccess: (calculado) => {
            setCosto(calculado);
            void queryClient.invalidateQueries({
                queryKey: ordenesServicioKeys.all,
            });
            notifications.show({
                color: "green",
                message: `Costo de la OS ${orden.id}: ${formatearPesos(calculado.total)}`,
            });
        },
        onError: (error: ApiError) => {
            if (error.code === "business_rule" || error.code === "conflict") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({
                    queryKey: ordenesServicioKeys.all,
                });
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const problema =
        [guardar.error, calcular.error].find(
            (error) =>
                error?.code === "business_rule" || error?.code === "conflict",
        ) ?? null;

    // Calcular con el form sucio costearía el estado viejo del servidor y mostraría
    // un número que no se corresponde con lo que hay en pantalla.
    const sucio = form.isDirty();

    return (
        <Modal
            opened
            onClose={onClose}
            size="55rem"
            title={`OS ${orden.id} — ${orden.transportista_razon_social}`}
        >
            <form
                onSubmit={form.onSubmit((valores) => guardar.mutate(valores))}
            >
                <Stack gap="md">
                    {problema && (
                        <Alert
                            color="red"
                            title="No se pudo completar la operación"
                        >
                            {problema.message}
                        </Alert>
                    )}

                    <Fieldset legend="Generales">
                        <Stack gap="sm">
                            <TextInput
                                label="Ubicación"
                                value={
                                    orden.origen_codigo
                                        ? `${orden.origen_nombre} (${orden.origen_codigo})`
                                        : orden.origen_nombre
                                }
                                readOnly
                            />

                            <SimpleGrid cols={{ base: 1, sm: 2 }}>
                                <DateTimePicker
                                    label="Fecha de viaje"
                                    placeholder="Sin fecha"
                                    clearable
                                    valueFormat="DD/MM/YYYY HH:mm"
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("fecha_viaje")}
                                />
                                <Select
                                    label="Tipo de operación"
                                    data={opciones.tipos_operacion}
                                    allowDeselect={false}
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("tipo_operacion")}
                                />
                                <Select
                                    label="Tipo de camión"
                                    data={opciones.tipos_camion}
                                    placeholder="Sin definir"
                                    clearable
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("tipo_camion")}
                                />
                                <Select
                                    label="Vía"
                                    data={opciones.vias}
                                    allowDeselect={false}
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("via")}
                                />
                            </SimpleGrid>

                            <Group gap="xl">
                                <Checkbox
                                    label="Con hombreador"
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("hombreador", {
                                        type: "checkbox",
                                    })}
                                />
                                <Checkbox
                                    label="Facturable"
                                    disabled={!puedeEditar}
                                    {...form.getInputProps("facturable", {
                                        type: "checkbox",
                                    })}
                                />
                            </Group>
                        </Stack>
                    </Fieldset>

                    <Fieldset legend={`Tickets (${detalle.tickets.length})`}>
                        <TicketsDeOrden tickets={detalle.tickets} />
                    </Fieldset>

                    <Fieldset legend={`Remitos (${detalle.remitos.length})`}>
                        {detalle.remitos.length > 0 ? (
                            <Stack gap="xs">
                                {detalle.remitos.map((remito) => (
                                    <FilaRemito key={remito.id} remito={remito} />
                                ))}
                            </Stack>
                        ) : (
                            <Text c="dimmed" size="sm">
                                Sin remitos asociados. Sin destinos no se puede resolver
                                la tarifa de flete.
                            </Text>
                        )}
                    </Fieldset>

                    <Fieldset legend="Costo">
                        <Stack gap="sm">
                            {costo ? (
                                <SimpleGrid
                                    cols={{ base: 2, sm: 4 }}
                                    spacing="xs"
                                >
                                    <Dato
                                        label="Flete"
                                        valor={formatearPesos(
                                            costo.precio_flete,
                                        )}
                                    />
                                    <Dato
                                        label={`Adicional (${costo.dias} día${costo.dias === 1 ? "" : "s"})`}
                                        valor={formatearPesos(
                                            costo.subtotal_adicional,
                                        )}
                                    />
                                    <Dato
                                        label="Modalidad"
                                        valor={`${costo.modalidad ?? "—"} · ${costo.cantidad_destinos} destino${costo.cantidad_destinos === 1 ? "" : "s"}`}
                                    />
                                    <Dato
                                        label="Total"
                                        valor={formatearPesos(costo.total)}
                                        destacado
                                    />
                                </SimpleGrid>
                            ) : (
                                <Text c="dimmed" size="sm">
                                    Esta orden todavía no tiene costo calculado.
                                </Text>
                            )}

                            <Group justify="space-between">
                                <Text c="dimmed" size="xs">
                                    {costo &&
                                        `Calculado el ${formatearFecha(costo.calculado_at)}`}
                                </Text>
                                <Can permiso="ordenes_servicio.calcular_costo">
                                    <Button
                                        variant="light"
                                        disabled={sucio}
                                        loading={calcular.isPending}
                                        onClick={() => calcular.mutate()}
                                    >
                                        {costo
                                            ? "Recalcular costo"
                                            : "Calcular costo"}
                                    </Button>
                                </Can>
                            </Group>
                            {sucio && (
                                <Text c="orange" size="xs">
                                    Guardá los cambios antes de calcular: el
                                    costo se calcula con los datos guardados en
                                    el servidor.
                                </Text>
                            )}
                        </Stack>
                    </Fieldset>

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>
                            {puedeEditar ? "Cancelar" : "Cerrar"}
                        </Button>
                        {puedeEditar && (
                            <Button
                                type="submit"
                                loading={guardar.isPending}
                                disabled={!sucio}
                            >
                                Guardar
                            </Button>
                        )}
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}

function FilaRemito({ remito }: { remito: RemitoOut }) {
    return (
        <Group gap="sm" wrap="wrap" align="center">
            <Text size="sm" fw={600} ff="monospace">
                {remito.numero}
            </Text>
            {remito.fecha && (
                <Text c="dimmed" size="sm">
                    {formatearFecha(remito.fecha)}
                </Text>
            )}
            {remito.destinos.length > 0 ? (
                remito.destinos.map((destino) => (
                    <Badge
                        key={destino.ubicacion_id}
                        variant="light"
                        size="sm"
                        title={destino.pais ?? "sin país"}
                    >
                        {destino.codigo ?? destino.nombre}
                    </Badge>
                ))
            ) : (
                <Text c="dimmed" size="sm">
                    sin destinos
                </Text>
            )}
        </Group>
    );
}

function Dato({
    label,
    valor,
    destacado = false,
}: {
    label: string;
    valor: string;
    destacado?: boolean;
}) {
    return (
        <div>
            <Text c="dimmed" size="xs">
                {label}
            </Text>
            <Text size={destacado ? "md" : "sm"} fw={destacado ? 700 : 400}>
                {valor}
            </Text>
        </div>
    );
}
