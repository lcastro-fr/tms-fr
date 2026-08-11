import { Group, Pagination, Table, Text, Box } from "@mantine/core";
import type {
    ColumnDef,
    RowSelectionState,
    SortingState,
} from "@tanstack/react-table";
import {
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";

import { BuscadorTabla } from "./BuscadorTabla";
import { filtroGlobalTexto } from "./filtro-global";

/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
export type ColumnDefs<T> = ColumnDef<T, any>[];

type Props<T> = {
    columns: ColumnDefs<T>;
    data: T[];
    getRowId: (row: T) => string;
    rowSelection?: RowSelectionState;
    onRowSelectionChange?: (selection: RowSelectionState) => void;
    vacio?: string;
    pageSize?: number;
    buscador?: string;
};

export function DataTable<T>({
    columns,
    data,
    getRowId,
    rowSelection,
    onRowSelectionChange,
    vacio = "Sin resultados",
    pageSize = 20,
    buscador,
}: Props<T>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [busqueda, setBusqueda] = useState("");

    const table = useReactTable({
        data,
        columns,
        getRowId,
        state: {
            sorting,
            globalFilter: busqueda,
            ...(rowSelection ? { rowSelection } : {}),
        },
        onSortingChange: setSorting,
        onGlobalFilterChange: setBusqueda,
        globalFilterFn: filtroGlobalTexto,
        getColumnCanGlobalFilter: () => true,
        enableRowSelection: rowSelection !== undefined,
        onRowSelectionChange: (updater) => {
            if (!onRowSelectionChange) return;
            const siguiente =
                typeof updater === "function"
                    ? updater(rowSelection ?? {})
                    : updater;
            onRowSelectionChange(siguiente);
        },
        initialState: { pagination: { pageSize } },
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
    });

    const totalPaginas = table.getPageCount();
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
                    {table.getRowModel().rows.map((row) => (
                        <Table.Tr
                            key={row.id}
                            bg={
                                row.getIsSelected()
                                    ? "var(--mantine-color-gold-light"
                                    : undefined
                            }
                        >
                            {row.getVisibleCells().map((cell) => (
                                <Table.Td key={cell.id}>
                                    {flexRender(
                                        cell.column.columnDef.cell,
                                        cell.getContext(),
                                    )}
                                </Table.Td>
                            ))}
                        </Table.Tr>
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
