import { CloseButton, TextInput } from "@mantine/core";

type Props = {
    placeholder: string;
    valor: string;
    onChange: (valor: string) => void;
};

export function BuscadorTabla({ placeholder, valor, onChange }: Props) {
    return (
        <TextInput
            aria-label="Buscar en la tabla"
            placeholder={placeholder}
            value={valor}
            onChange={(event) => onChange(event.currentTarget.value)}
            w={320}
            rightSection={
                valor !== "" ? (
                    <CloseButton
                        size="sm"
                        aria-label="Limpiar la búsqueda"
                        onClick={() => onChange("")}
                    />
                ) : null
            }
        />
    );
}
