import {
    Alert,
    Button,
    Fieldset,
    Group,
    Input,
    Modal,
    Select,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { ApiError, fieldErrors } from "../../../api/errors";
import { MapaBase } from "../../../components/MapaBase";
import { SelectorPunto } from "../../../components/SelectorPunto";
import { aLatLng } from "../../../lib/geojson";
import { actualizarUbicacion, ubicacionesKeys } from "../api";
import type {
    GeoJSONPoint,
    TipoUbicacion,
    UbicacionIn,
    UbicacionOut,
} from "../api";
import { useUbicaciones } from "../use-ubicaciones";
import { CapaUbicaciones } from "./CapaUbicaciones";
import { ControlUbicaciones } from "./ControlUbicaciones";

const TIPOS: { value: TipoUbicacion; label: string }[] = [
    { value: "planta", label: "Planta" },
    { value: "puerto", label: "Puerto" },
    { value: "aeropuerto", label: "Aeropuerto" },
    { value: "cliente", label: "Cliente" },
    { value: "otro", label: "Otro" },
];

type Props = {
    ubicacion: UbicacionOut;
    onClose: () => void;
};

type Valores = {
    nombre: string;
    tipo: TipoUbicacion;
    coordinates: GeoJSONPoint | null;
};

export function UbicacionFormModal({ ubicacion, onClose }: Props) {
    const queryClient = useQueryClient();

    const form = useForm<Valores>({
        initialValues: {
            nombre: ubicacion.nombre,
            tipo: (ubicacion.tipo as TipoUbicacion) ?? "cliente",
            coordinates: ubicacion.coordinates,
        },
        validate: {
            nombre: (valor) => (valor.trim() ? null : "Ingresá un nombre"),
            coordinates: (valor) =>
                valor ? null : "Marcá la coordenada en el mapa",
        },
    });

    const [centro] = useState(() =>
        ubicacion.coordinates ? aLatLng(ubicacion.coordinates) : undefined,
    );
    const esPlanta = ubicacion.tipo === "planta";

    const ubicaciones = useUbicaciones();
    const vecinas = useMemo(
        () => ubicaciones.dibujables.filter((u) => u.id !== ubicacion.id),
        [ubicaciones.dibujables, ubicacion.id],
    );

    const mutation = useMutation({
        mutationFn: ({ nombre, tipo, coordinates }: Valores) => {
            if (!coordinates) {
                throw new Error(
                    "Sin coordenada: el validate del form tendría que haberlo frenado",
                );
            }
            const payload: UbicacionIn = {
                nombre: nombre.trim(),
                tipo,
                coordinates,
            };
            return actualizarUbicacion(ubicacion.id, payload);
        },
        onSuccess: (guardada) => {
            void queryClient.invalidateQueries({
                queryKey: ubicacionesKeys.all,
            });
            notifications.show({
                color: "green",
                message: `Se validó la ubicación ${guardada.nombre}`,
            });
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
            if (error.code === "business_rule") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({
                    queryKey: ubicacionesKeys.all,
                });
                onClose();
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const reglaDeNegocio =
        mutation.error?.code === "business_rule" ? mutation.error : null;

    return (
        <Modal
            opened
            onClose={onClose}
            size="70rem"
            title={
                ubicacion.codigo
                    ? `${ubicacion?.nombre} (${ubicacion?.codigo})`
                    : ubicacion?.nombre
            }
            closeOnEscape={false}
            closeOnClickOutside={false}
        >
            <form
                onSubmit={form.onSubmit((valores) => mutation.mutate(valores))}
            >
                <Stack gap="md">
                    {reglaDeNegocio && (
                        <Alert color="red" title="La coordenada no es válida">
                            {reglaDeNegocio.message}
                        </Alert>
                    )}

                    {esPlanta && (
                        <Alert color="yellow" title="Es una planta">
                            Cambiarle el tipo hace que la ingesta de SAP rechace
                            los tickets que la usan como planta de origen.
                        </Alert>
                    )}

                    <Group grow align="flex-start">
                        <TextInput
                            label="Nombre"
                            maxLength={120}
                            {...form.getInputProps("nombre")}
                        />
                        <Select
                            label="Tipo"
                            data={TIPOS}
                            allowDeselect={false}
                            {...form.getInputProps("tipo")}
                        />
                    </Group>

                    <Fieldset legend="Dirección de referencia">
                        <Stack gap="xs">
                            <TextInput
                                label="Calle"
                                value={ubicacion?.calle ?? ""}
                                readOnly
                            />
                            <Group grow align="flex-start">
                                <TextInput
                                    label="Localidad"
                                    value={ubicacion?.localidad ?? ""}
                                    readOnly
                                />
                                <TextInput
                                    label="Provincia"
                                    value={ubicacion?.provincia ?? ""}
                                    readOnly
                                />
                                <TextInput
                                    label="País"
                                    value={ubicacion.pais ?? ""}
                                    readOnly
                                />
                            </Group>
                        </Stack>
                    </Fieldset>

                    <div>
                        <Input.Label>Coordenada</Input.Label>
                        <Text size="xs" c="dimmed" mb="xs">
                            Clickeá el mapa para ubicar el punto, o arrastrá el
                            marcador. Al guardar, la ubicación queda validada.
                        </Text>
                        <Group mb="xs">
                            <ControlUbicaciones
                                puedeVer={ubicaciones.puedeVer}
                                mostrar={ubicaciones.mostrar}
                                onMostrar={ubicaciones.setMostrar}
                                cargando={ubicaciones.cargando}
                                fallo={ubicaciones.fallo}
                                sinCoordenadas={ubicaciones.sinCoordenadas}
                            />
                        </Group>
                        <MapaBase center={centro} zoom={centro ? 14 : 4}>
                            <SelectorPunto
                                valor={form.values.coordinates}
                                onChange={(punto) =>
                                    form.setFieldValue("coordinates", punto)
                                }
                            />
                            {ubicaciones.mostrar && (
                                <CapaUbicaciones ubicaciones={vecinas} />
                            )}
                        </MapaBase>
                        {form.errors.coordinates && (
                            <Input.Error mt="xs">
                                {form.errors.coordinates}
                            </Input.Error>
                        )}
                    </div>

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" loading={mutation.isPending}>
                            Guardar y validar
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}
