import { ActionIcon, Button, Group, NumberInput, Select, Table, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";

import type { TarifarioOpcionesOut } from "../api";
import type { Valores } from "./valores-tarifario";
import { filaConceptoVacia } from "./valores-tarifario";

type Props = {
    form: UseFormReturnType<Valores>;
    opciones: TarifarioOpcionesOut;
    soloLectura: boolean;
};

export function FilasTarifaConcepto({ form, opciones, soloLectura }: Props) {
    const conceptos = opciones.conceptos.map((c) => ({
        value: String(c.id),
        label: `${c.codigo} — ${c.nombre}`,
    }));
    const unidadPorId = new Map(opciones.conceptos.map((c) => [String(c.id), c.unidad]));

    return (
        <>
            <Table verticalSpacing="xs" horizontalSpacing="xs">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Concepto</Table.Th>
                        <Table.Th w={140}>Unidad</Table.Th>
                        <Table.Th w={170}>Precio</Table.Th>
                        <Table.Th w={40} />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {form.values.tarifas_concepto.map((fila, indice) => {
                        const bloqueada = soloLectura || fila.congelada;
                        return (
                        <Table.Tr key={fila.key}>
                            <Table.Td>
                                <Select
                                    aria-label="Concepto"
                                    searchable
                                    nothingFoundMessage="Sin resultados"
                                    placeholder="Elegí un concepto"
                                    data={conceptos}
                                    disabled={bloqueada}
                                    {...form.getInputProps(
                                        `tarifas_concepto.${indice}.concepto_id`,
                                    )}
                                />
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm" c="dimmed">
                                    {unidadPorId.get(fila.concepto_id ?? "") ?? "—"}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                <NumberInput
                                    aria-label="Precio"
                                    decimalScale={2}
                                    fixedDecimalScale
                                    hideControls
                                    min={0}
                                    thousandSeparator="."
                                    decimalSeparator=","
                                    prefix="$ "
                                    disabled={bloqueada}
                                    {...form.getInputProps(`tarifas_concepto.${indice}.precio`)}
                                />
                            </Table.Td>
                            <Table.Td>
                                {!bloqueada && (
                                    <ActionIcon
                                        aria-label="Quitar concepto"
                                        variant="subtle"
                                        color="red"
                                        onClick={() =>
                                            form.removeListItem("tarifas_concepto", indice)
                                        }
                                    >
                                        ✕
                                    </ActionIcon>
                                )}
                            </Table.Td>
                        </Table.Tr>
                        );
                    })}
                </Table.Tbody>
            </Table>

            {form.values.tarifas_concepto.length === 0 && (
                <Text c="dimmed" size="sm">
                    Sin conceptos adicionales. Una operación de cámara no se puede costear sin
                    uno.
                </Text>
            )}

            {typeof form.errors.tarifas_concepto === "string" && (
                <Text c="red" size="sm" mt="xs">
                    {form.errors.tarifas_concepto}
                </Text>
            )}

            {!soloLectura && (
                <Group mt="xs">
                    <Button
                        size="xs"
                        variant="light"
                        disabled={form.values.tarifas_concepto.length >= opciones.conceptos.length}
                        onClick={() =>
                            form.insertListItem("tarifas_concepto", filaConceptoVacia())
                        }
                    >
                        Agregar concepto
                    </Button>
                </Group>
            )}
        </>
    );
}
