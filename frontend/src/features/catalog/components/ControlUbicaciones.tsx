import { Group, Loader, Switch, Text } from "@mantine/core";

type Props = {
    puedeVer: boolean;
    mostrar: boolean;
    onMostrar: (mostrar: boolean) => void;
    cargando: boolean;
    fallo: boolean;
    sinCoordenadas: number;
};

export function ControlUbicaciones({
    puedeVer,
    mostrar,
    onMostrar,
    cargando,
    fallo,
    sinCoordenadas,
}: Props) {
    if (!puedeVer) {
        return null;
    }

    return (
        <Group gap="sm">
            <Switch
                label="Mostrar ubicaciones"
                checked={mostrar}
                onChange={(event) => onMostrar(event.currentTarget.checked)}
            />
            {cargando && <Loader size="xs" />}
            {fallo && (
                <Text c="red" size="xs">
                    No se pudieron cargar las ubicaciones.
                </Text>
            )}
            {/* Que no se dibujen no puede quedar en silencio: el usuario está justamente
                verificando que el polígono cubra todos los puntos. */}
            {mostrar && !cargando && sinCoordenadas > 0 && (
                <Text c="dimmed" size="xs">
                    {sinCoordenadas} sin coordenadas, no se dibujan.
                </Text>
            )}
        </Group>
    );
}
