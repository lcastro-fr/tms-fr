import { Badge, Group, Table, Text } from "@mantine/core";

import { formatearFecha } from "../../../lib/date";
import type { TicketOut } from "../api";

type Props = {
    tickets: TicketOut[];
};

function dias(cantidad: number): string {
    return cantidad === 1 ? "1 día" : `${cantidad} días`;
}

export function TicketsDeOrden({ tickets }: Props) {
    if (tickets.length === 0) {
        return (
            <Text c="dimmed" size="sm">
                Esta orden no tiene tickets asociados.
            </Text>
        );
    }

    const conEstadia = tickets.filter((t) => t.dias_estadia !== null);
    const total = conEstadia.reduce((suma, t) => suma + (t.dias_estadia ?? 0), 0);

    return (
        <>
            <Table withTableBorder withColumnBorders={false} verticalSpacing="xs">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Ticket</Table.Th>
                        <Table.Th>Planta</Table.Th>
                        <Table.Th>Ingreso</Table.Th>
                        <Table.Th>Egreso</Table.Th>
                        <Table.Th ta="right">Estadía</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {tickets.map((ticket) => (
                        <Table.Tr key={ticket.id}>
                            <Table.Td>
                                <Text size="sm" fw={600} ff="monospace">
                                    {ticket.numero}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm">
                                    {ticket.planta_codigo
                                        ? `${ticket.planta_nombre} (${ticket.planta_codigo})`
                                        : ticket.planta_nombre}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                <Text size="sm">
                                    {formatearFecha(ticket.fecha_ingreso)}
                                </Text>
                            </Table.Td>
                            <Table.Td>
                                {ticket.fecha_egreso ? (
                                    <Text size="sm">
                                        {formatearFecha(ticket.fecha_egreso)}
                                    </Text>
                                ) : (
                                    // Sin egreso el costeo muere con TicketSinEgresoError.
                                    <Badge color="orange" variant="light" size="sm">
                                        sin egreso
                                    </Badge>
                                )}
                            </Table.Td>
                            <Table.Td ta="right">
                                {ticket.dias_estadia === null ? (
                                    <Text c="dimmed" size="sm">
                                        —
                                    </Text>
                                ) : (
                                    <Text size="sm">{dias(ticket.dias_estadia)}</Text>
                                )}
                            </Table.Td>
                        </Table.Tr>
                    ))}
                </Table.Tbody>
            </Table>

            {tickets.length > 1 && (
                <Group justify="flex-end" mt="xs">
                    <Text c="dimmed" size="xs">
                        Estadía total: {dias(total)}
                        {conEstadia.length < tickets.length &&
                            ` (sin contar ${tickets.length - conEstadia.length} sin egreso)`}
                    </Text>
                </Group>
            )}
        </>
    );
}
