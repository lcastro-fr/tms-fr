import {
    Alert,
    Badge,
    Button,
    Checkbox,
    Divider,
    Group,
    Loader,
    MultiSelect,
    ScrollArea,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import type { ApiError } from "../../../api/errors";
import { normalizarTexto } from "../../../lib/texto";
import { unirDivisiones } from "../api";
import type { UnionDivisionesOut } from "../api";
import type { Divisiones } from "../use-divisiones";

type Props = {
    divisiones: Divisiones;
    onUnion: (resultado: UnionDivisionesOut) => void;
};

export function SelectorDivisiones({ divisiones, onUnion }: Props) {
    const [filtro, setFiltro] = useState("");

    const mutation = useMutation({
        mutationFn: unirDivisiones,
        onSuccess: onUnion,
    });

    const opcionesProvincia = useMemo(
        () =>
            divisiones.provincias.map((provincia) => ({
                value: provincia.codigo,
                label: `${provincia.nombre} (${provincia.cantidad_departamentos})`,
            })),
        [divisiones.provincias],
    );

    const gruposVisibles = useMemo(() => {
        const aguja = normalizarTexto(filtro.trim());
        if (!aguja) {
            return divisiones.grupos;
        }
        return divisiones.grupos.map((grupo) => ({
            ...grupo,
            departamentos: grupo.departamentos.filter((d) =>
                normalizarTexto(d.nombre).includes(aguja),
            ),
        }));
    }, [divisiones.grupos, filtro]);

    const sinCoincidencias =
        filtro.trim() !== "" &&
        gruposVisibles.every((g) => g.departamentos.length === 0);

    const error = mutation.error as ApiError | null;

    return (
        <Stack gap="sm">
            {divisiones.fallo && (
                <Alert
                    color="red"
                    title="No se pudo cargar la división política"
                >
                    Ocurrio un error. Por favor vuelva a intentar.
                </Alert>
            )}

            {error && (
                <Alert color="red" title="No se pudo componer la geometría">
                    {error.message}
                </Alert>
            )}

            <MultiSelect
                label="Provincias"
                placeholder={
                    divisiones.provinciasElegidas.length > 0
                        ? undefined
                        : divisiones.cargandoProvincias
                          ? "Cargando…"
                          : "Elegí una o más"
                }
                data={opcionesProvincia}
                value={divisiones.provinciasElegidas}
                onChange={divisiones.elegirProvincias}
                disabled={divisiones.cargandoProvincias}
                searchable
                clearable
                hidePickedOptions
            />

            {divisiones.provinciasElegidas.length > 0 && (
                <>
                    <Group gap="xs" align="center">
                        <TextInput
                            placeholder="Filtrar departamentos"
                            value={filtro}
                            onChange={(evento) =>
                                setFiltro(evento.currentTarget.value)
                            }
                            flex={1}
                        />
                        {divisiones.cargandoDepartamentos && (
                            <Loader size="sm" />
                        )}
                    </Group>

                    <ScrollArea.Autosize mah={260} type="auto">
                        <Stack gap="xs">
                            {gruposVisibles.map((grupo, indice) => {
                                const entera =
                                    divisiones.provinciasMarcadas.has(
                                        grupo.provincia.codigo,
                                    );
                                return (
                                    <Stack key={grupo.provincia.codigo} gap={4}>
                                        {indice > 0 && <Divider />}
                                        <Checkbox
                                            label={
                                                <Text size="sm" fw={600}>
                                                    Toda{" "}
                                                    {grupo.provincia.nombre}
                                                </Text>
                                            }
                                            checked={entera}
                                            onChange={() =>
                                                divisiones.toggleProvincia(
                                                    grupo.provincia.codigo,
                                                )
                                            }
                                        />
                                        {grupo.cargando && (
                                            <Text size="sm" c="dimmed" pl="lg">
                                                Cargando departamentos…
                                            </Text>
                                        )}
                                        {grupo.departamentos.map(
                                            (departamento) => (
                                                <Checkbox
                                                    key={departamento.codigo}
                                                    pl="lg"
                                                    label={departamento.nombre}
                                                    // Con la provincia entera ya están incluidos:
                                                    // marcarlos aparte sería el mismo polígono dos
                                                    // veces.
                                                    checked={divisiones.codigosDibujadosMarcados.has(
                                                        departamento.codigo,
                                                    )}
                                                    disabled={entera}
                                                    onChange={() =>
                                                        divisiones.toggleDepartamento(
                                                            departamento.codigo,
                                                        )
                                                    }
                                                />
                                            ),
                                        )}
                                    </Stack>
                                );
                            })}
                            {sinCoincidencias && (
                                <Text size="sm" c="dimmed">
                                    Ningún departamento coincide con &quot;
                                    {filtro}&quot;.
                                </Text>
                            )}
                        </Stack>
                    </ScrollArea.Autosize>
                </>
            )}

            {divisiones.cantidad > 0 && (
                <Group gap="xs">
                    {[...divisiones.provinciasMarcadas].map((codigo) => (
                        <Badge
                            key={codigo}
                            variant="filled"
                            onClick={() => divisiones.toggleProvincia(codigo)}
                            style={{ cursor: "pointer" }}
                        >
                            {divisiones.nombreDe(codigo)} (toda)
                        </Badge>
                    ))}
                    {[...divisiones.departamentosMarcados].map((codigo) => (
                        <Badge
                            key={codigo}
                            variant="light"
                            onClick={() =>
                                divisiones.toggleDepartamento(codigo)
                            }
                            style={{ cursor: "pointer" }}
                        >
                            {divisiones.nombreDe(codigo)}
                        </Badge>
                    ))}
                </Group>
            )}

            <Group justify="space-between">
                <Text size="sm" c="dimmed">
                    {divisiones.cantidad === 0
                        ? "Marcá provincias o departamentos, en la lista o en el mapa."
                        : `${divisiones.cantidad} marcadas.`}
                </Text>
                <Group gap="xs">
                    <Button
                        variant="default"
                        size="xs"
                        disabled={divisiones.cantidad === 0}
                        onClick={() => divisiones.limpiar()}
                    >
                        Limpiar
                    </Button>
                    <Button
                        size="xs"
                        disabled={divisiones.cantidad === 0}
                        loading={mutation.isPending}
                        onClick={() => mutation.mutate(divisiones.seleccion)}
                    >
                        Componer geometría
                    </Button>
                </Group>
            </Group>
        </Stack>
    );
}
