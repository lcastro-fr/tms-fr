import { Badge, Button, Group, Text } from "@mantine/core";

import type { ColumnDefs } from "../../components/DataTable";
import type { UbicacionOut } from "./api";

type Acciones = {
    onEditar: (ubicacion: UbicacionOut) => void;
    puedeEditar: boolean;
};

export function ubicacionesColumns({ onEditar, puedeEditar }: Acciones): ColumnDefs<UbicacionOut> {
    return [
        { accessorKey: "codigo", header: "Código" },
        { accessorKey: "nombre", header: "Nombre" },
        // Valor tabulado: su filtro es un Select por columna, no la búsqueda de texto libre.
        { accessorKey: "tipo", header: "Tipo", enableGlobalFilter: false },
        { accessorKey: "localidad", header: "Localidad" },
        { accessorKey: "provincia", header: "Provincia" },
        {
            id: "coordenada",
            header: "Coordenada",
            enableSorting: false,
            cell: ({ row }) => {
                const punto = row.original.coordinates;
                if (!punto) {
                    return (
                        <Text c="dimmed" size="sm">
                            sin coordenadas
                        </Text>
                    );
                }
                const [lng, lat] = punto.coordinates;
                return (
                    <Text size="sm" ff="monospace">
                        {lat.toFixed(5)}, {lng.toFixed(5)}
                    </Text>
                );
            },
        },
        {
            id: "validada",
            header: "Estado",
            enableSorting: false,
            cell: ({ row }) =>
                row.original.validada ? (
                    <Badge color="green" variant="light">
                        Validada
                    </Badge>
                ) : (
                    <Badge color="orange" variant="light">
                        Pendiente
                    </Badge>
                ),
        },
        {
            id: "acciones",
            header: "",
            enableSorting: false,
            cell: ({ row }) => (
                <Group gap="xs" justify="flex-end" wrap="nowrap">
                    {puedeEditar && (
                        <Button size="xs" variant="subtle" onClick={() => onEditar(row.original)}>
                            Editar
                        </Button>
                    )}
                </Group>
            ),
        },
    ];
}
