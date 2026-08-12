import {
    ActionIcon,
    Badge,
    Button,
    Group,
    Select,
    Table,
    Text,
} from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { Pencil } from "@phosphor-icons/react/Pencil";
import { Fragment, useMemo } from "react";

import type { UbicacionOpcionOut } from "../api";
import type { Valores } from "./valores-orden-servicio";
import { filaDestinoVacia } from "./valores-orden-servicio";

type Props = {
    form: UseFormReturnType<Valores>;
    ubicaciones: UbicacionOpcionOut[];
    disabled: boolean;
    onEditarUbicacion?: (id: number) => void;
};

export function FilasDestinoOrden({
    form,
    ubicaciones,
    disabled,
    onEditarUbicacion,
}: Props) {
    const opciones = useMemo(
        () =>
            ubicaciones.map((u) => ({
                value: String(u.id),
                label: u.codigo
                    ? `${u.codigo} — ${u.nombre} - ${u.localidad} - ${u.provincia}`
                    : u.nombre,
            })),
        [ubicaciones],
    );
    const porId = useMemo(
        () => new Map(ubicaciones.map((u) => [String(u.id), u])),
        [ubicaciones],
    );

    return (
        <>
            <Table verticalSpacing="xs" horizontalSpacing="xs">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Ubicación</Table.Th>
                        <Table.Th w={200}>Tipo</Table.Th>
                        <Table.Th w={76} />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {form.values.destinos.map((fila, indice) => {
                        const elegida = fila.ubicacion_id
                            ? porId.get(fila.ubicacion_id)
                            : undefined;
                        return (
                            <Fragment key={fila.key}>
                                <Table.Tr>
                                    <Table.Td>
                                        <Select
                                            aria-label="Ubicación del destino"
                                            searchable
                                            limit={50}
                                            nothingFoundMessage="Sin resultados"
                                            placeholder="Buscá por código o nombre"
                                            data={opciones}
                                            disabled={disabled}
                                            {...form.getInputProps(
                                                `destinos.${indice}.ubicacion_id`,
                                            )}
                                        />
                                    </Table.Td>
                                    <Table.Td>
                                        {elegida && (
                                            <Group gap="xs">
                                                <Badge
                                                    variant="light"
                                                    size="sm"
                                                >
                                                    {elegida.tipo}
                                                </Badge>
                                                {/* Sin coordenadas la tarifa por zona falla al costear. */}
                                                {!elegida.tiene_coordenadas && (
                                                    <Badge
                                                        color="orange"
                                                        variant="light"
                                                        size="sm"
                                                        title="Sin coordenadas: no se puede resolver la zona"
                                                    >
                                                        sin geo
                                                    </Badge>
                                                )}
                                            </Group>
                                        )}
                                    </Table.Td>
                                    <Table.Td>
                                        <Group gap={4} wrap="nowrap">
                                            {onEditarUbicacion && elegida && (
                                                <ActionIcon
                                                    aria-label="Editar ubicación"
                                                    title="Editar la ubicación sin cerrar la orden"
                                                    variant="subtle"
                                                    color={
                                                        elegida.tiene_coordenadas
                                                            ? undefined
                                                            : "orange"
                                                    }
                                                    onClick={() =>
                                                        onEditarUbicacion(
                                                            elegida.id,
                                                        )
                                                    }
                                                >
                                                    <Pencil size={16} />
                                                </ActionIcon>
                                            )}
                                            {!disabled && (
                                                <ActionIcon
                                                    aria-label="Quitar destino"
                                                    variant="subtle"
                                                    color="red"
                                                    onClick={() =>
                                                        form.removeListItem(
                                                            "destinos",
                                                            indice,
                                                        )
                                                    }
                                                >
                                                    ✕
                                                </ActionIcon>
                                            )}
                                        </Group>
                                    </Table.Td>
                                </Table.Tr>
                                {/* El backend puede rechazar la fila entera: ese loc no cae en
                                    ningún input, así que se muestra acá. */}
                                {form.errors[`destinos.${indice}`] && (
                                    <Table.Tr>
                                        <Table.Td colSpan={3}>
                                            <Text c="red" size="sm">
                                                {
                                                    form.errors[
                                                        `destinos.${indice}`
                                                    ]
                                                }
                                            </Text>
                                        </Table.Td>
                                    </Table.Tr>
                                )}
                            </Fragment>
                        );
                    })}
                </Table.Tbody>
            </Table>

            {typeof form.errors.destinos === "string" && (
                <Text c="red" size="sm" mt="xs">
                    {form.errors.destinos}
                </Text>
            )}

            {!disabled && (
                <Group mt="xs">
                    <Button
                        size="xs"
                        variant="light"
                        onClick={() =>
                            form.insertListItem("destinos", filaDestinoVacia())
                        }
                    >
                        Agregar destino
                    </Button>
                </Group>
            )}
        </>
    );
}
