import { ActionIcon, Button, Group, NumberInput, Select, Table, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { Fragment } from "react";

import type { TarifarioOpcionesOut } from "../api";
import type { FilaFlete, Valores } from "./valores-tarifario";
import { filaFleteVacia } from "./valores-tarifario";

type Props = {
    form: UseFormReturnType<Valores>;
    opciones: TarifarioOpcionesOut;
    soloLectura: boolean;
};

const ALCANCES = [
    { value: "zona", label: "Zona" },
    { value: "ubicacion", label: "Ubicación" },
];

export function FilasTarifaFlete({ form, opciones, soloLectura }: Props) {
    const zonas = opciones.zonas.map((z) => ({ value: String(z.id), label: z.nombre }));
    const ubicaciones = opciones.ubicaciones.map((u) => ({
        value: String(u.id),
        label: u.codigo ? `${u.codigo} — ${u.nombre}` : u.nombre,
    }));
    const modalidades = opciones.modalidades.map((o) => ({ value: o.value, label: o.label }));
    const tiposCamion = opciones.tipos_camion.map((o) => ({ value: o.value, label: o.label }));

    const cambiarAlcance = (indice: number, alcance: FilaFlete["alcance"]) => {
        form.setFieldValue(`tarifas_flete.${indice}.alcance`, alcance);
        form.setFieldValue(`tarifas_flete.${indice}.referencia_id`, null);
    };

    return (
        <>
            <Table verticalSpacing="xs" horizontalSpacing="xs">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th w={140}>Alcance</Table.Th>
                        <Table.Th>Zona / Ubicación</Table.Th>
                        <Table.Th w={160}>Modalidad</Table.Th>
                        <Table.Th w={150}>Tipo de camión</Table.Th>
                        <Table.Th w={140}>Hombreador</Table.Th>
                        <Table.Th w={170}>Precio</Table.Th>
                        <Table.Th w={40} />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {form.values.tarifas_flete.map((fila, indice) => (
                        <Fragment key={fila.key}>
                            <Table.Tr>
                                <Table.Td>
                                    <Select
                                        aria-label="Alcance"
                                        data={ALCANCES}
                                        allowDeselect={false}
                                        disabled={soloLectura}
                                        value={fila.alcance}
                                        onChange={(valor) =>
                                            cambiarAlcance(indice, valor as FilaFlete["alcance"])
                                        }
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <Select
                                        aria-label={fila.alcance === "zona" ? "Zona" : "Ubicación"}
                                        // ~1785 ubicaciones: sin searchable el select es inusable.
                                        searchable
                                        limit={50}
                                        nothingFoundMessage="Sin resultados"
                                        placeholder={
                                            fila.alcance === "zona"
                                                ? "Elegí una zona"
                                                : "Buscá por código o nombre"
                                        }
                                        data={fila.alcance === "zona" ? zonas : ubicaciones}
                                        disabled={soloLectura}
                                        {...form.getInputProps(`tarifas_flete.${indice}.referencia_id`)}
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <Select
                                        aria-label="Modalidad"
                                        data={modalidades}
                                        allowDeselect={false}
                                        disabled={soloLectura}
                                        {...form.getInputProps(`tarifas_flete.${indice}.modalidad`)}
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <Select
                                        aria-label="Tipo de camión"
                                        data={tiposCamion}
                                        allowDeselect={false}
                                        disabled={soloLectura}
                                        {...form.getInputProps(`tarifas_flete.${indice}.tipo_camion`)}
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <Select
                                        aria-label="Hombreador"
                                        data={[
                                            { value: "false", label: "Sin hombreador" },
                                            { value: "true", label: "Con hombreador" },
                                        ]}
                                        allowDeselect={false}
                                        disabled={soloLectura}
                                        value={String(fila.hombreador)}
                                        onChange={(valor) =>
                                            form.setFieldValue(
                                                `tarifas_flete.${indice}.hombreador`,
                                                valor === "true",
                                            )
                                        }
                                    />
                                </Table.Td>
                                <Table.Td>
                                    <NumberInput
                                        aria-label="Precio"
                                        // El precio queda string de punta a punta: nunca se hace
                                        // aritmética de pesos en float.
                                        decimalScale={2}
                                        fixedDecimalScale
                                        hideControls
                                        min={0}
                                        thousandSeparator="."
                                        decimalSeparator=","
                                        prefix="$ "
                                        disabled={soloLectura}
                                        {...form.getInputProps(`tarifas_flete.${indice}.precio`)}
                                    />
                                </Table.Td>
                                <Table.Td>
                                    {!soloLectura && (
                                        <ActionIcon
                                            aria-label="Quitar tarifa de flete"
                                            variant="subtle"
                                            color="red"
                                            onClick={() => form.removeListItem("tarifas_flete", indice)}
                                        >
                                            ✕
                                        </ActionIcon>
                                    )}
                                </Table.Td>
                            </Table.Tr>
                            {/* El backend puede rechazar la fila entera (el XOR zona/ubicación):
                                ese loc no cae en ningún input, así que se muestra acá. */}
                            {form.errors[`tarifas_flete.${indice}`] && (
                                <Table.Tr>
                                    <Table.Td colSpan={7}>
                                        <Text c="red" size="sm">
                                            {form.errors[`tarifas_flete.${indice}`]}
                                        </Text>
                                    </Table.Td>
                                </Table.Tr>
                            )}
                        </Fragment>
                    ))}
                </Table.Tbody>
            </Table>

            {form.values.tarifas_flete.length === 0 && (
                <Text c="dimmed" size="sm">
                    Sin tarifas de flete. Sin al menos una, este tarifario sólo sirve para
                    operaciones de cámara.
                </Text>
            )}

            {typeof form.errors.tarifas_flete === "string" && (
                <Text c="red" size="sm" mt="xs">
                    {form.errors.tarifas_flete}
                </Text>
            )}

            {!soloLectura && (
                <Group mt="xs">
                    <Button
                        size="xs"
                        variant="light"
                        onClick={() => form.insertListItem("tarifas_flete", filaFleteVacia())}
                    >
                        Agregar tarifa de flete
                    </Button>
                </Group>
            )}
        </>
    );
}
