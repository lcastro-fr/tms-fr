import {
    Alert,
    Button,
    Group,
    Input,
    Modal,
    Stack,
    Tabs,
    Text,
    TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, fieldErrors } from "../../../api/errors";
import { MapaBase } from "../../../components/MapaBase";
import { verticesDistintos } from "../../../lib/geojson";
import { formatearKm2 } from "../../../lib/numero";
import { actualizarZona, crearZona, zonasKeys } from "../api";
import type {
    GeoJSONMultiPolygon,
    UnionDivisionesOut,
    ZonaIn,
    ZonaOut,
} from "../api";
import { useDivisiones } from "../use-divisiones";
import { useUbicaciones } from "../use-ubicaciones";
import { CapaDivisiones } from "./CapaDivisiones";
import { CapaUbicaciones } from "./CapaUbicaciones";
import { ControlUbicaciones } from "./ControlUbicaciones";
import { EditorPolygono } from "./EditorPolygono";
import type { Semilla } from "./EditorPolygono";
import { SelectorDivisiones } from "./SelectorDivisiones";

type Props = {
    zona: ZonaOut | null;
    onClose: () => void;
};

type Valores = {
    nombre: string;
    geom: GeoJSONMultiPolygon | null;
};

export function ZonaFormModal({ zona, onClose }: Props) {
    const queryClient = useQueryClient();
    const ubicaciones = useUbicaciones();
    const divisiones = useDivisiones();
    const [semilla, setSemilla] = useState<Semilla | null>(null);
    const [compuesta, setCompuesta] = useState<UnionDivisionesOut | null>(null);
    const [pestana, setPestana] = useState<string | null>("dibujar");

    const form = useForm<Valores>({
        initialValues: { nombre: zona?.nombre ?? "", geom: zona?.geom ?? null },
        validate: {
            nombre: (valor) => (valor.trim() ? null : "Ingresá un nombre"),
            geom: (valor) => {
                if (!valor)
                    return "Dibujá la zona en el mapa o componela con divisiones";
                return verticesDistintos(valor) >= 3
                    ? null
                    : "Al menos tres vértices distintos";
            },
        },
    });

    const mutation = useMutation({
        mutationFn: ({ nombre, geom }: Valores) => {
            if (!geom) {
                throw new Error(
                    "Sin geometría: el validate del form tendría que haberlo frenado",
                );
            }
            const payload: ZonaIn = { nombre: nombre.trim(), geom };
            return zona ? actualizarZona(zona.id, payload) : crearZona(payload);
        },
        onSuccess: (guardada) => {
            void queryClient.invalidateQueries({ queryKey: zonasKeys.all });
            notifications.show({
                color: "green",
                message: `Se guardó la zona ${guardada.nombre}`,
            });
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
            if (error.code === "conflict") {
                form.setErrors({ nombre: error.message });
                return;
            }
            if (error.code === "business_rule") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({ queryKey: zonasKeys.all });
                onClose();
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const reglaDeNegocio =
        mutation.error?.code === "business_rule" ? mutation.error : null;
    const motivo = reglaDeNegocio?.detail.motivo;

    const alComponer = (resultado: UnionDivisionesOut) => {
        setCompuesta(resultado);
        setSemilla((previa) => ({
            geom: resultado.geom,
            version: (previa?.version ?? 0) + 1,
        }));
    };

    return (
        <Modal
            opened
            onClose={onClose}
            size="80rem"
            title={zona ? `Editar ${zona.nombre}` : "Nueva zona"}
            closeOnEscape={false}
            closeOnClickOutside={false}
        >
            <form
                onSubmit={form.onSubmit((valores) => mutation.mutate(valores))}
            >
                <Stack gap="md">
                    {reglaDeNegocio && (
                        <Alert color="red" title="La geometría no es válida">
                            {reglaDeNegocio.message}
                            {typeof motivo === "string" &&
                            motivo.includes("Self-intersection")
                                ? " — revisá que el contorno no se cruce a sí mismo."
                                : null}
                        </Alert>
                    )}

                    <TextInput
                        label="Nombre"
                        maxLength={120}
                        {...form.getInputProps("nombre")}
                    />

                    <Group align="flex-start" gap="md" wrap="nowrap">
                        <Stack gap="sm" w={340} style={{ flexShrink: 0 }}>
                            <Tabs value={pestana} onChange={setPestana}>
                                <Tabs.List>
                                    <Tabs.Tab value="dibujar">Dibujar</Tabs.Tab>
                                    <Tabs.Tab value="divisiones">
                                        División política
                                    </Tabs.Tab>
                                </Tabs.List>

                                <Tabs.Panel value="dibujar" pt="sm">
                                    <ControlUbicaciones
                                        puedeVer={ubicaciones.puedeVer}
                                        mostrar={ubicaciones.mostrar}
                                        onMostrar={ubicaciones.setMostrar}
                                        cargando={ubicaciones.cargando}
                                        fallo={ubicaciones.fallo}
                                        sinCoordenadas={
                                            ubicaciones.sinCoordenadas
                                        }
                                    />
                                </Tabs.Panel>

                                <Tabs.Panel value="divisiones" pt="sm">
                                    <SelectorDivisiones
                                        divisiones={divisiones}
                                        onUnion={alComponer}
                                    />
                                </Tabs.Panel>
                            </Tabs>

                            {compuesta && (
                                <Alert
                                    color="blue"
                                    title="Geometría compuesta"
                                    p="xs"
                                >
                                    <Text size="sm">
                                        {compuesta.poligonos === 1
                                            ? "Un polígono"
                                            : `${compuesta.poligonos} polígonos separados`}{" "}
                                        de {compuesta.vertices} vértices,{" "}
                                        {formatearKm2(compuesta.superficie_km2)} km².
                                    </Text>
                                </Alert>
                            )}
                        </Stack>

                        <div style={{ flex: 1, minWidth: 0 }}>
                            <MapaBase>
                                <EditorPolygono
                                    valor={zona?.geom ?? null}
                                    semilla={semilla}
                                    onChange={(geom) =>
                                        form.setFieldValue("geom", geom)
                                    }
                                />
                                {pestana === "divisiones" && (
                                    <CapaDivisiones
                                        divisiones={divisiones.departamentos}
                                        marcados={
                                            divisiones.codigosDibujadosMarcados
                                        }
                                        onToggle={divisiones.toggleDepartamento}
                                    />
                                )}
                                {pestana === "dibujar" &&
                                    ubicaciones.mostrar && (
                                        <CapaUbicaciones
                                            ubicaciones={ubicaciones.dibujables}
                                        />
                                    )}
                            </MapaBase>
                            {form.errors.geom && (
                                <Input.Error mt="xs">
                                    {form.errors.geom}
                                </Input.Error>
                            )}
                        </div>
                    </Group>

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" loading={mutation.isPending}>
                            Guardar
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}
