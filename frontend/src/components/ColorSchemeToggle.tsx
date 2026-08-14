import { ActionIcon, useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { Moon } from "@phosphor-icons/react/Moon";
import { Sun } from "@phosphor-icons/react/Sun";

export function ColorSchemeToggle() {
    const { setColorScheme } = useMantineColorScheme();
    const computed = useComputedColorScheme("light", { getInitialValueInEffect: true });
    const esOscuro = computed === "dark";
    const label = esOscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro";

    return (
        <ActionIcon
            variant="default"
            size="lg"
            aria-label={label}
            title={label}
            onClick={() => setColorScheme(esOscuro ? "light" : "dark")}
        >
            {esOscuro ? <Sun size={18} /> : <Moon size={18} />}
        </ActionIcon>
    );
}
