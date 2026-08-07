import { Badge, Button, Group } from "@mantine/core";

import type { ColumnDefs } from "../../components/DataTable";
import { formatearFecha } from "../../lib/date";
import type { TarifarioOut } from "./api";

type Acciones = {
    onAbrir: (tarifario: TarifarioOut) => void;
    onDuplicar: (tarifario: TarifarioOut) => void;
    onCerrar: (tarifario: TarifarioOut) => void;
    onEliminar: (tarifario: TarifarioOut) => void;
    puedeEditar: boolean;
    puedeCrear: boolean;
    puedeEliminar: boolean;
};

export function tarifariosColumns({
    onAbrir,
    onDuplicar,
    onCerrar,
    onEliminar,
    puedeEditar,
    puedeCrear,
    puedeEliminar,
}: Acciones): ColumnDefs<TarifarioOut> {
    return [
        { accessorKey: "transportista_razon_social", header: "Transportista" },
        {
            accessorKey: "vigente_desde",
            header: "Vigente desde",
            cell: ({ row }) => formatearFecha(row.original.vigente_desde),
        },
        {
            accessorKey: "vigente_hasta",
            header: "Vigente hasta",
            cell: ({ row }) => formatearFecha(row.original.vigente_hasta, "Sin cierre"),
        },
        { accessorKey: "cantidad_fletes", header: "Fletes" },
        { accessorKey: "cantidad_conceptos", header: "Conceptos" },
        {
            id: "estado",
            header: "Estado",
            enableSorting: false,
            cell: ({ row }) =>
                row.original.en_uso ? (
                    <Badge color="orange" variant="light">
                        En uso
                    </Badge>
                ) : (
                    <Badge color="gray" variant="light">
                        Editable
                    </Badge>
                ),
        },
        {
            id: "acciones",
            header: "",
            enableSorting: false,
            cell: ({ row }) => {
                const tarifario = row.original;
                // Un tarifario ya usado para costear no se edita ni se da de baja: la salida
                // es cerrar su vigencia y duplicarlo.
                const editable = puedeEditar && !tarifario.en_uso;
                return (
                    <Group gap="xs" justify="flex-end" wrap="nowrap">
                        <Button size="xs" variant="subtle" onClick={() => onAbrir(tarifario)}>
                            {editable ? "Editar" : "Ver"}
                        </Button>
                        {puedeCrear && (
                            <Button
                                size="xs"
                                variant="subtle"
                                onClick={() => onDuplicar(tarifario)}
                            >
                                Duplicar
                            </Button>
                        )}
                        {puedeEditar && tarifario.vigente_hasta === null && (
                            <Button size="xs" variant="subtle" onClick={() => onCerrar(tarifario)}>
                                Cerrar vigencia
                            </Button>
                        )}
                        {puedeEliminar && !tarifario.en_uso && (
                            <Button
                                size="xs"
                                variant="subtle"
                                color="red"
                                onClick={() => onEliminar(tarifario)}
                            >
                                Dar de baja
                            </Button>
                        )}
                    </Group>
                );
            },
        },
    ];
}
