import { Alert, Button, Group, Input, Modal, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, fieldErrors } from "../../../api/errors";
import { MapaBase } from "../../../components/MapaBase";
import { verticesDistintos } from "../../../lib/geojson";
import { actualizarZona, crearZona, zonasKeys } from "../api";
import type { GeoJSONPolygon, ZonaIn, ZonaOut } from "../api";
import { useUbicaciones } from "../use-ubicaciones";
import { CapaUbicaciones } from "./CapaUbicaciones";
import { ControlUbicaciones } from "./ControlUbicaciones";
import { EditorPolygono } from "./EditorPolygono";

type Props = {
    zona: ZonaOut | null;
    onClose: () => void;
};

type Valores = {
    nombre: string;
    geom: GeoJSONPolygon | null;
};

export function ZonaFormModal({ zona, onClose }: Props) {
    const queryClient = useQueryClient();
    const ubicaciones = useUbicaciones();
    const [errorGeom, setErrorGeom] = useState<string | null>(null);

    const form = useForm<Valores>({
        initialValues: { nombre: zona?.nombre ?? "", geom: zona?.geom ?? null },
        validate: {
            nombre: (valor) => (valor.trim() ? null : "Ingresá un nombre"),
            geom: (valor) => {
                if (!valor) return "Dibujá la zona en el mapa";
                return verticesDistintos(valor) >= 3 ? null : "Al menos tres vértices distintos";
            },
        },
    });

    const mutation = useMutation({
        mutationFn: ({ nombre, geom }: Valores) => {
            if (!geom) {
                throw new Error("Sin geometría: el validate del form tendría que haberlo frenado");
            }
            const payload: ZonaIn = { nombre: nombre.trim(), geom };
            return zona ? actualizarZona(zona.id, payload) : crearZona(payload);
        },
        onSuccess: (guardada) => {
            void queryClient.invalidateQueries({ queryKey: zonasKeys.all });
            notifications.show({ color: "green", message: `Se guardó la zona ${guardada.nombre}` });
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

    const reglaDeNegocio = mutation.error?.code === "business_rule" ? mutation.error : null;
    const motivo = reglaDeNegocio?.detail.motivo;

    return (
        <Modal
            opened
            onClose={onClose}
            size="80rem"
            title={zona ? `Editar ${zona.nombre}` : "Nueva zona"}
            closeOnEscape={false}
            closeOnClickOutside={false}
        >
            <form onSubmit={form.onSubmit((valores) => mutation.mutate(valores))}>
                <Stack gap="md">
                    {reglaDeNegocio && (
                        <Alert color="red" title="La geometría no es válida">
                            {reglaDeNegocio.message}
                            {typeof motivo === "string" && motivo.includes("Self-intersection")
                                ? " — revisá que el contorno no se cruce a sí mismo."
                                : null}
                        </Alert>
                    )}
                    {errorGeom && (
                        <Alert color="red" title="No se puede guardar">
                            {errorGeom}
                        </Alert>
                    )}

                    <TextInput
                        label="Nombre"
                        maxLength={120}
                        {...form.getInputProps("nombre")}
                    />

                    <ControlUbicaciones
                        puedeVer={ubicaciones.puedeVer}
                        mostrar={ubicaciones.mostrar}
                        onMostrar={ubicaciones.setMostrar}
                        cargando={ubicaciones.cargando}
                        fallo={ubicaciones.fallo}
                        sinCoordenadas={ubicaciones.sinCoordenadas}
                    />

                    <div>
                        <MapaBase>
                            <EditorPolygono
                                valor={zona?.geom ?? null}
                                onChange={(geom) => {
                                    setErrorGeom(null);
                                    form.setFieldValue("geom", geom);
                                }}
                                onMultiPolygon={() =>
                                    setErrorGeom(
                                        "La edición partió la zona en dos. El modelo guarda un solo polígono.",
                                    )
                                }
                            />
                            {ubicaciones.mostrar && (
                                <CapaUbicaciones ubicaciones={ubicaciones.dibujables} />
                            )}
                        </MapaBase>
                        {form.errors.geom && (
                            <Input.Error mt="xs">{form.errors.geom}</Input.Error>
                        )}
                    </div>

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
