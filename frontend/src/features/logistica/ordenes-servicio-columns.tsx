import { Badge, Button, Group, Text } from "@mantine/core";

import type { ColumnDefs } from "../../components/DataTable";
import { formatearFecha } from "../../lib/date";
import { formatearPesos } from "../../lib/money";
import type { OrdenServicioOut } from "./api";

type Acciones = {
    onEditar: (orden: OrdenServicioOut) => void;
    onCalcular: (orden: OrdenServicioOut) => void;
    onEliminar: (orden: OrdenServicioOut) => void;
    puedeEditar: boolean;
    puedeCalcular: boolean;
    puedeEliminar: boolean;
    calculandoId: number | null;
    etiqueta: (
        grupo: "tipos_operacion" | "tipos_camion" | "vias",
        value: string | null,
    ) => string;
};

export function ordenesServicioColumns({
    onEditar,
    onCalcular,
    onEliminar,
    puedeEditar,
    puedeCalcular,
    puedeEliminar,
    calculandoId,
    etiqueta,
}: Acciones): ColumnDefs<OrdenServicioOut> {
    return [
        { accessorKey: "id", header: "OS", size: 60 },
        {
            id: "tickets",
            header: "Ticket",
            accessorFn: (orden) => orden.tickets.map((t) => t.numero).join(" "),
            cell: ({ row }) =>
                row.original.tickets.length > 0 ? (
                    <Group gap={4} wrap="nowrap">
                        {row.original.tickets.map((ticket) => (
                            <Text key={ticket.id} size="sm" ff="monospace">
                                {ticket.numero}
                            </Text>
                        ))}
                    </Group>
                ) : (
                    <Text c="dimmed" size="sm">
                        sin ticket
                    </Text>
                ),
        },
        {
            id: "origen",
            header: "Origen",
            accessorFn: (orden) => orden.origen_nombre,
            cell: ({ row }) => (
                <Text size="sm">
                    {row.original.origen_nombre}
                    {row.original.origen_codigo && (
                        <Text span c="dimmed" size="xs">
                            {" "}
                            ({row.original.origen_codigo})
                        </Text>
                    )}
                </Text>
            ),
        },
        { accessorKey: "transportista_razon_social", header: "Transportista" },
        {
            accessorKey: "fecha_viaje",
            header: "Fecha de viaje",
            // El accessor es el ISO y la celda muestra DD/MM/YYYY: buscar "11/08" no daría nada.
            enableGlobalFilter: false,
            cell: ({ row }) =>
                row.original.fecha_viaje ? (
                    formatearFecha(row.original.fecha_viaje)
                ) : (
                    <Text c="dimmed" size="sm">
                        sin fecha
                    </Text>
                ),
        },
        // Los tres son valores tabulados: su filtro es un Select por columna, no texto libre.
        {
            id: "tipo_operacion",
            header: "Operación",
            accessorFn: (orden) => orden.tipo_operacion,
            enableGlobalFilter: false,
            cell: ({ row }) =>
                etiqueta("tipos_operacion", row.original.tipo_operacion),
        },
        {
            id: "via",
            header: "Vía",
            accessorFn: (orden) => orden.via,
            enableGlobalFilter: false,
            cell: ({ row }) => etiqueta("vias", row.original.via),
        },
        {
            id: "tipo_camion",
            header: "Camión",
            accessorFn: (orden) => orden.tipo_camion ?? "",
            enableGlobalFilter: false,
            cell: ({ row }) =>
                row.original.tipo_camion ? (
                    etiqueta("tipos_camion", row.original.tipo_camion)
                ) : (
                    <Text c="dimmed" size="sm">
                        sin definir
                    </Text>
                ),
        },
        {
            id: "flags",
            header: "",
            enableSorting: false,
            cell: ({ row }) => (
                <Group gap="xs" wrap="nowrap">
                    {row.original.facturable && (
                        <Badge color="green" variant="light" size="sm">
                            Facturable
                        </Badge>
                    )}
                    {row.original.hombreador && (
                        <Badge color="orange" variant="light" size="sm">
                            Hombreador
                        </Badge>
                    )}
                </Group>
            ),
        },
        {
            id: "costo",
            header: "Costo teórico",
            accessorFn: (orden) =>
                orden.costo ? Number(orden.costo.total) : -1,
            enableGlobalFilter: false,
            meta: { numerico: true },
            cell: ({ row }) =>
                row.original.costo ? (
                    <Text size="sm" fw={500}>
                        {formatearPesos(row.original.costo.total)}
                    </Text>
                ) : (
                    <Text c="dimmed" size="sm">
                        sin calcular
                    </Text>
                ),
        },
        {
            id: "costo_real",
            header: "Costo real",
            accessorFn: (orden) =>
                orden.costo_real ? Number(orden.costo_real) : -1,
            enableGlobalFilter: false,
            meta: { numerico: true },
            cell: ({ row }) =>
                row.original.costo_real ? (
                    <Text size="sm" fw={500}>
                        {formatearPesos(row.original.costo_real)}
                    </Text>
                ) : (
                    <Text c="dimmed" size="sm">
                        sin cargar
                    </Text>
                ),
        },
        {
            id: "acciones",
            header: "",
            enableSorting: false,
            cell: ({ row }) => (
                <Group gap="xs" justify="flex-end" wrap="nowrap">
                    {puedeCalcular && (
                        <Button
                            size="xs"
                            variant="subtle"
                            loading={calculandoId === row.original.id}
                            onClick={() => onCalcular(row.original)}
                        >
                            {row.original.costo ? "Recalcular" : "Calcular"}
                        </Button>
                    )}
                    <Button
                        size="xs"
                        variant="subtle"
                        onClick={() => onEditar(row.original)}
                    >
                        {puedeEditar ? "Editar" : "Ver"}
                    </Button>
                    {puedeEliminar && (
                        <Button
                            size="xs"
                            variant="subtle"
                            color="red"
                            onClick={() => onEliminar(row.original)}
                        >
                            Eliminar
                        </Button>
                    )}
                </Group>
            ),
        },
    ];
}
