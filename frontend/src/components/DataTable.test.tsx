import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { theme } from "../app/theme";
import { DataTable, type ColumnDefs } from "./DataTable";

type Fila = {
    id: number;
    codigo: string;
    localidad: string | null;
    tipo: string;
    costo: number;
};

// La primera fila va con localidad null a propósito: es el caso que el default de TanStack
// resuelve mal, dejando la columna afuera de la búsqueda para toda la tabla.
const FILAS: Fila[] = [
    { id: 1, codigo: "AAA", localidad: null, tipo: "expreso", costo: -1 },
    { id: 2, codigo: "BBB", localidad: "Rosario", tipo: "puerto", costo: 1500 },
    { id: 3, codigo: "CCC", localidad: "Córdoba", tipo: "cliente", costo: 250 },
];

const COLUMNS: ColumnDefs<Fila> = [
    { accessorKey: "codigo", header: "Código" },
    { accessorKey: "localidad", header: "Localidad" },
    { accessorKey: "tipo", header: "Tipo", enableGlobalFilter: false },
    { accessorKey: "costo", header: "Costo", enableGlobalFilter: false },
    {
        id: "acciones",
        header: "",
        cell: ({ row }) => <span>ver {row.original.codigo}</span>,
    },
];

type Opciones = {
    data?: Fila[];
    buscador?: string | null;
    pageSize?: number;
    vacio?: string;
};

function renderTabla({
    data = FILAS,
    buscador = "Código o localidad",
    pageSize,
    vacio,
}: Opciones = {}) {
    return render(
        <MantineProvider theme={theme}>
            <DataTable
                columns={COLUMNS}
                data={data}
                getRowId={(fila) => String(fila.id)}
                buscador={buscador ?? undefined}
                pageSize={pageSize}
                vacio={vacio}
            />
        </MantineProvider>,
    );
}

const buscar = (texto: string) =>
    userEvent.type(screen.getByRole("textbox", { name: "Buscar en la tabla" }), texto);

describe("DataTable con buscador", () => {
    it("busca en una columna nullable aunque la primera fila sea null", async () => {
        renderTabla();

        await buscar("rosario");

        expect(screen.getByText("BBB")).toBeInTheDocument();
        expect(screen.queryByText("AAA")).not.toBeInTheDocument();
        expect(screen.queryByText("CCC")).not.toBeInTheDocument();
    });

    it.each(["cordoba", "CÓRDOBA", "CORDOBA"])(
        "encuentra Córdoba tipeando %s",
        async (termino) => {
            renderTabla();

            await buscar(termino);

            expect(screen.getByText("CCC")).toBeInTheDocument();
            expect(screen.queryByText("BBB")).not.toBeInTheDocument();
        },
    );

    it("no busca en las columnas con enableGlobalFilter en false", async () => {
        renderTabla();

        await buscar("expreso");

        expect(screen.getByText(/Ninguna fila coincide/)).toBeInTheDocument();
        expect(screen.queryByText("AAA")).not.toBeInTheDocument();
    });

    it("no busca en el costo, que es el número crudo con -1 de centinela", async () => {
        renderTabla();

        await buscar("1500");

        expect(screen.getByText(/Ninguna fila coincide/)).toBeInTheDocument();
    });

    it("no busca en las columnas de display, que no tienen accessor", async () => {
        renderTabla();

        await buscar("ver");

        expect(screen.getByText(/Ninguna fila coincide/)).toBeInTheDocument();
    });

    it("muestra el conteo de coincidencias sobre el total", async () => {
        renderTabla();

        await buscar("rosario");

        expect(screen.getByText("1 de 3")).toBeInTheDocument();
    });

    it("con la tabla vacía muestra el mensaje del caller y no el de la búsqueda", () => {
        renderTabla({ data: [], vacio: "Todavía no hay filas." });

        expect(screen.getByText("Todavía no hay filas.")).toBeInTheDocument();
        expect(screen.queryByText(/Ninguna fila coincide/)).not.toBeInTheDocument();
    });

    it("sin coincidencias muestra el término buscado y no el mensaje del caller", async () => {
        renderTabla({ vacio: "Todavía no hay filas." });

        await buscar("zzz");

        expect(screen.getByText("Ninguna fila coincide con “zzz”.")).toBeInTheDocument();
        expect(screen.queryByText("Todavía no hay filas.")).not.toBeInTheDocument();
    });

    it("vuelve a la primera página al buscar", async () => {
        renderTabla({ pageSize: 2 });

        await userEvent.click(screen.getByRole("button", { name: "2" }));
        expect(screen.getByText("CCC")).toBeInTheDocument();

        await buscar("rosario");

        // El reset del pageIndex cae en un microtask, de ahí el findByText.
        expect(await screen.findByText("BBB")).toBeInTheDocument();
    });

    it("el botón de limpiar restituye las filas", async () => {
        renderTabla();
        const input = screen.getByRole("textbox", { name: "Buscar en la tabla" });

        await buscar("rosario");
        expect(screen.queryByText("AAA")).not.toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: "Limpiar la búsqueda" }));

        expect(screen.getByText("AAA")).toBeInTheDocument();
        expect(input).toHaveValue("");
    });

    it("sin el prop buscador no hay barra de búsqueda", () => {
        renderTabla({ buscador: null });

        expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
        expect(screen.getByText("AAA")).toBeInTheDocument();
    });
});
