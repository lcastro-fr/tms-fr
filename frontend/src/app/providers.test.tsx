import { Button } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Providers } from "./providers";

test("monta el arbol de providers y renderiza un componente de Mantine", () => {
    render(
        <Providers>
            <Button>Guardar</Button>
        </Providers>,
    );

    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
});

test("expone el queryClient a los hijos", async () => {
    function Consumidor() {
        const { data } = useQuery({
            queryKey: ["ping"],
            queryFn: () => Promise.resolve("pong"),
        });

        return <span>{data ?? "..."}</span>;
    }

    render(
        <Providers>
            <Consumidor />
        </Providers>,
    );

    expect(await screen.findByText("pong")).toBeInTheDocument();
});
