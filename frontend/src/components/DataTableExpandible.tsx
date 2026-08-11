import { ActionIcon, Box, Group, Pagination, Table, Text } from "@mantine/core";
import type { ExpandedState, SortingState } from "@tanstack/react-table";
import {
    flexRender,
    getCoreRowModel,
    getExpandedRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from "@tanstack/react-table";
import type { ReactNode } from "react";
import { Fragment, useState } from "react";

import { BuscadorTabla } from "./BuscadorTabla";
import type { ColumnDefs } from "./DataTable";
import { filtroGlobalTexto } from "./filtro-global";

type Props<T> = {
    columns: ColumnDefs<T>;
    data: T[];
    getRowId: (row: T) => string;
    /** El panel de la fila abierta. Se llama sólo cuando está expandida. */
    expandido: (row: T) => ReactNode;
    puedeExpandir?: (row: T) => boolean;
    vacio?: string;
    pageSize?: number;
    /** El placeholder de la barra de búsqueda. Sin este prop no hay barra. */
    buscador?: string;
};

/**
 * Hermano de DataTable para las listas que tienen un detalle por fila. Son dos componentes
 * y no uno con props opcionales: la selección de filas sólo aplica a uno y la expansión
 * sólo al otro.
 */
export function DataTableExpandible<T>({
    columns,
    data,
    getRowId,
    expandido,
    puedeExpandir = () => true,
    vacio = "Sin resultados",
    pageSize = 20,
    buscador,
}: Props<T>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [expanded, setExpanded] = useState<ExpandedState>({});
    const [busqueda, setBusqueda] = useState("");

    const table = useReactTable({
        data,
        columns,
        getRowId,
        state: { sorting, expanded, globalFilter: busqueda },
        onSortingChange: setSorting,
        onExpandedChange: setExpanded,
        onGlobalFilterChange: setBusqueda,
        globalFilterFn: filtroGlobalTexto,
        // Igual que en DataTable: sin esto, una columna nullable que arranca en null queda
        // afuera de la búsqueda para toda la tabla. El detalle de la fila no es un sub-row,
        // así que la búsqueda es sobre los padres y nada más.
        getColumnCanGlobalFilter: () => true,
        getRowCanExpand: (row) => puedeExpandir(row.original),
        initialState: { pagination: { pageSize } },
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getExpandedRowModel: getExpandedRowModel(),
    });

    const totalPaginas = table.getPageCount();
    // El colSpan tiene que cubrir las celdas más la del chevron, o la tabla se desalinea.
    const columnasTotales = table.getVisibleFlatColumns().length + 1;
    // Pre-paginación: getPaginationRowModel no clampea el pageIndex, así que el conteo de la
    // página es 0 por un commit cada vez que la búsqueda achica los resultados.
    const coincidencias = table.getFilteredRowModel().rows.length;

    return (
        <Box
            style={{
                borderRadius: "var(--mantine-radius-md)",
                overflow: "hidden",
                border: "1px solid var(--mantine-color-default-border)",
                padding: "var(--mantine-spacing-xs)",
            }}
        >
            {buscador !== undefined && (
                <Group justify="space-between" mb="xs" wrap="nowrap">
                    <BuscadorTabla
                        placeholder={buscador}
                        valor={busqueda}
                        onChange={setBusqueda}
                    />
                    {busqueda !== "" && (
                        <Text c="dimmed" size="sm">
                            {coincidencias} de {data.length}
                        </Text>
                    )}
                </Group>
            )}

            <Table striped highlightOnHover>
                <Table.Thead>
                    {table.getHeaderGroups().map((grupo) => (
                        <Table.Tr key={grupo.id}>
                            <Table.Th w={40} />
                            {grupo.headers.map((header) => (
                                <Table.Th
                                    key={header.id}
                                    onClick={header.column.getToggleSortingHandler()}
                                    style={
                                        header.column.getCanSort()
                                            ? { cursor: "pointer" }
                                            : undefined
                                    }
                                >
                                    {flexRender(
                                        header.column.columnDef.header,
                                        header.getContext(),
                                    )}
                                </Table.Th>
                            ))}
                        </Table.Tr>
                    ))}
                </Table.Thead>
                <Table.Tbody>
                    {/* Dos <tr> por fila: el fragmento es lo que los mantiene hermanos. */}
                    {table.getRowModel().rows.map((row) => (
                        <Fragment key={row.id}>
                            <Table.Tr>
                                <Table.Td>
                                    {row.getCanExpand() && (
                                        <ActionIcon
                                            variant="subtle"
                                            color="gray"
                                            size="sm"
                                            aria-expanded={row.getIsExpanded()}
                                            aria-label={
                                                row.getIsExpanded()
                                                    ? "Contraer la fila"
                                                    : "Expandir la fila"
                                            }
                                            onClick={row.getToggleExpandedHandler()}
                                        >
                                            <Chevron abierto={row.getIsExpanded()} />
                                        </ActionIcon>
                                    )}
                                </Table.Td>
                                {row.getVisibleCells().map((cell) => (
                                    <Table.Td key={cell.id}>
                                        {flexRender(
                                            cell.column.columnDef.cell,
                                            cell.getContext(),
                                        )}
                                    </Table.Td>
                                ))}
                            </Table.Tr>
                            {row.getIsExpanded() && (
                                <Table.Tr>
                                    <Table.Td colSpan={columnasTotales} p="md">
                                        {expandido(row.original)}
                                    </Table.Td>
                                </Table.Tr>
                            )}
                        </Fragment>
                    ))}
                </Table.Tbody>
            </Table>

            {data.length === 0 && (
                <Text c="dimmed" size="sm" mt="sm">
                    {vacio}
                </Text>
            )}

            {data.length > 0 && coincidencias === 0 && (
                <Text c="dimmed" size="sm" mt="sm">
                    Ninguna fila coincide con “{busqueda}”.
                </Text>
            )}

            {totalPaginas > 1 && (
                <Group justify="flex-end" mt="sm">
                    <Pagination
                        total={totalPaginas}
                        value={table.getState().pagination.pageIndex + 1}
                        onChange={(pagina) => table.setPageIndex(pagina - 1)}
                    />
                </Group>
            )}
        </Box>
    );
}

function Chevron({ abierto }: { abierto: boolean }) {
    return (
        <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            style={{
                transform: abierto ? "rotate(90deg)" : undefined,
                transition: "transform 150ms ease",
            }}
        >
            <path d="m9 18 6-6-6-6" />
        </svg>
    );
}
