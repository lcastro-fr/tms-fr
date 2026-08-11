import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ColorSchemeToggle } from "./ColorSchemeToggle";

function montar() {
    return render(
        <MantineProvider defaultColorScheme="light">
            <ColorSchemeToggle />
        </MantineProvider>,
    );
}

test("alterna entre modo claro y oscuro al hacer click", async () => {
    const user = userEvent.setup();
    montar();

    expect(
        screen.getByRole("button", { name: "Cambiar a modo oscuro" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cambiar a modo oscuro" }));

    expect(
        screen.getByRole("button", { name: "Cambiar a modo claro" }),
    ).toBeInTheDocument();
});
