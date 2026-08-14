import { Button, Checkbox, Group } from "@mantine/core";

import type { ColumnDefs } from "../../components/DataTable";
import { verticesDistintos } from "../../lib/geojson";
import { formatearKm2 } from "../../lib/numero";
import type { ZonaOut } from "./api";

type Acciones = {
    onEditar: (zona: ZonaOut) => void;
    onEliminar: (zona: ZonaOut) => void;
    puedeEditar: boolean;
    puedeEliminar: boolean;
};

export function zonasColumns({
    onEditar,
    onEliminar,
    puedeEditar,
    puedeEliminar,
}: Acciones): ColumnDefs<ZonaOut> {
    return [
        {
            id: "seleccion",
            enableSorting: false,
            size: 40,
            header: ({ table }) => (
                <Checkbox
                    aria-label="Seleccionar todas las zonas de la página"
                    checked={table.getIsAllPageRowsSelected()}
                    indeterminate={
                        table.getIsSomePageRowsSelected() && !table.getIsAllPageRowsSelected()
                    }
                    onChange={(event) =>
                        table.toggleAllPageRowsSelected(event.currentTarget.checked)
                    }
                />
            ),
            cell: ({ row }) => (
                <Checkbox
                    aria-label={`Seleccionar ${row.original.nombre}`}
                    checked={row.getIsSelected()}
                    onChange={row.getToggleSelectedHandler()}
                />
            ),
        },
        { accessorKey: "nombre", header: "Nombre" },
        {
            id: "superficie",
            header: "Superficie (km²)",
            // Numérico y no accessorKey: sobre el string del Decimal el orden sería lexicográfico.
            accessorFn: (zona) => Number(zona.superficie_km2),
            enableGlobalFilter: false,
            meta: { numerico: true },
            cell: ({ row }) => formatearKm2(row.original.superficie_km2),
        },
        {
            id: "vertices",
            header: "Vértices",
            enableSorting: false,
            meta: { numerico: true },
            cell: ({ row }) => verticesDistintos(row.original.geom),
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
