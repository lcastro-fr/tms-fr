import { createTheme, type MantineColorsTuple } from "@mantine/core";

interface CustomColor {
    key: string;
    colors: MantineColorsTuple;
}

const GOLD: CustomColor = {
    key: "gold",
    colors: [
        "#fcf6ea",
        "#efe9dd",
        "#dcd1be",
        "#c8b79b",
        "#b8a17f",
        "#ad946c",
        "#a98d60",
        "#94794f",
        "#846c44",
        "#735c35",
    ],
};

export const theme = createTheme({
    primaryColor: GOLD.key,
    colors: {
        [GOLD.key]: GOLD.colors,
    },
    other: {
        zonaPalette: [
            "blue",
            "grape",
            "teal",
            "orange",
            "cyan",
            "pink",
            "lime",
            "violet",
        ],
    },
});

declare module "@mantine/core" {
    export interface MantineThemeOther {
        zonaPalette: string[];
    }
}
