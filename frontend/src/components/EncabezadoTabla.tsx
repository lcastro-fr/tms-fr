import { Group, Table, UnstyledButton } from "@mantine/core";
import { CaretDown } from "@phosphor-icons/react/CaretDown";
import { CaretUp } from "@phosphor-icons/react/CaretUp";
import { CaretUpDown } from "@phosphor-icons/react/CaretUpDown";
import type { Header, SortDirection } from "@tanstack/react-table";
import { flexRender } from "@tanstack/react-table";

import styles from "./EncabezadoTabla.module.css";

const ARIA_SORT = { asc: "ascending", desc: "descending" } as const;

type Props<T> = {
    header: Header<T, unknown>;
};

/**
 * El `<th>` de las dos tablas. Una columna que no se puede ordenar no lleva botón ni ícono:
 * el afford tiene que aparecer sólo donde hay algo que apretar.
 */
export function EncabezadoTabla<T>({ header }: Props<T>) {
    const columna = header.column;
    const contenido = flexRender(columna.columnDef.header, header.getContext());

    if (!columna.getCanSort()) {
        return <Table.Th>{contenido}</Table.Th>;
    }

    const orden = columna.getIsSorted();

    return (
        <Table.Th aria-sort={orden ? ARIA_SORT[orden] : "none"}>
            <UnstyledButton
                className={styles.boton}
                onClick={columna.getToggleSortingHandler()}
            >
                <Group gap={4} wrap="nowrap">
                    {contenido}
                    <IconoOrden orden={orden} />
                </Group>
            </UnstyledButton>
        </Table.Th>
    );
}

function IconoOrden({ orden }: { orden: false | SortDirection }) {
    if (orden === "asc") {
        return <CaretUp size={14} weight="bold" />;
    }
    if (orden === "desc") {
        return <CaretDown size={14} weight="bold" />;
    }
    // El caret neutro atenuado es la única señal de que la columna se puede ordenar.
    return <CaretUpDown size={14} style={{ opacity: 0.4 }} />;
}
