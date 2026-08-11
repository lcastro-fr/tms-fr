import { Alert, Button, Fieldset, Group, Modal, Select, Stack } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";

import { ApiError, fieldErrors } from "../../../api/errors";
import { usePermisos } from "../../auth";
import {
    actualizarTarifario,
    crearTarifario,
    tarifarioOpcionesQueryOptions,
    tarifarioQueryOptions,
    tarifariosKeys,
} from "../api";
import type { TarifarioDetalleOut, TarifarioOpcionesOut } from "../api";
import { FilasTarifaConcepto } from "./FilasTarifaConcepto";
import { FilasTarifaFlete } from "./FilasTarifaFlete";
import type { Valores } from "./valores-tarifario";
import { aPayload, claveFlete, valoresDuplicados, valoresIniciales } from "./valores-tarifario";

/** `duplicado` carga el contenido de otro tarifario pero da de alta uno nuevo. */
export type Modo = "alta" | "edicion" | "duplicado";

type Props = {
    tarifarioId: number | null;
    modo: Modo;
    onClose: () => void;
};

export function TarifarioFormModal({ tarifarioId, modo, onClose }: Props) {
    return (
        <Modal
            opened
            onClose={onClose}
            size="90rem"
            closeOnEscape={false}
            closeOnClickOutside={false}
            title={
                { alta: "Nuevo tarifario", duplicado: "Duplicar tarifario", edicion: "Tarifario" }[
                    modo
                ]
            }
        >
            {tarifarioId === null ? (
                <Formulario detalle={null} modo={modo} onClose={onClose} />
            ) : (
                <ConDetalle tarifarioId={tarifarioId} modo={modo} onClose={onClose} />
            )}
        </Modal>
    );
}

function ConDetalle({ tarifarioId, modo, onClose }: Props & { tarifarioId: number }) {
    const { data: detalle } = useSuspenseQuery(tarifarioQueryOptions(tarifarioId));
    return <Formulario detalle={detalle} modo={modo} onClose={onClose} />;
}

type FormularioProps = {
    detalle: TarifarioDetalleOut | null;
    modo: Modo;
    onClose: () => void;
};

function precioValido(precio: string | number): boolean {
    const numero = Number(precio);
    return String(precio).trim() !== "" && Number.isFinite(numero) && numero > 0;
}

function Formulario({ detalle, modo, onClose }: FormularioProps) {
    const queryClient = useQueryClient();
    const { can } = usePermisos();
    const { data: opciones } = useSuspenseQuery(tarifarioOpcionesQueryOptions());

    const editandoExistente = modo === "edicion" && detalle !== null;
    const enUso = detalle?.en_uso ?? false;
    // Sin permiso todo queda en sólo lectura. En uso el permiso alcanza para agregar filas:
    // las existentes y los metadatos quedan bloqueados fila por fila (`congelada`) y en el header.
    const puedeGuardar = editandoExistente ? can("tarifarios.editar") : can("tarifarios.crear");
    const soloLectura = !puedeGuardar;

    const form = useForm<Valores>({
        initialValues:
            modo === "duplicado" && detalle !== null
                ? valoresDuplicados(detalle)
                : valoresIniciales(detalle, enUso),
        validate: {
            transportista_id: (valor) => (valor ? null : "Elegí un transportista"),
            vigente_desde: (valor) => (valor ? null : "Ingresá desde cuándo rige"),
            tarifas_flete: {
                referencia_id: (valor) => (valor ? null : "Elegí una zona o una ubicación"),
                precio: (valor) => (precioValido(valor) ? null : "Ingresá un precio mayor a 0"),
            },
            tarifas_concepto: {
                concepto_id: (valor) => (valor ? null : "Elegí un concepto"),
                precio: (valor) => (precioValido(valor) ? null : "Ingresá un precio mayor a 0"),
            },
        },
    });

    /** El 409 del backend es el backstop; acá se avisa antes de mandar. */
    const sinDuplicados = (valores: Valores): boolean => {
        if (valores.tarifas_flete.length === 0 && valores.tarifas_concepto.length === 0) {
            form.setFieldError("tarifas_flete", "Cargá al menos una tarifa");
            return false;
        }

        const claves = new Set<string>();
        for (const fila of valores.tarifas_flete) {
            const clave = claveFlete(fila);
            if (claves.has(clave)) {
                form.setFieldError(
                    "tarifas_flete",
                    "Hay dos tarifas de flete con el mismo alcance, modalidad, tipo de camión y hombreador",
                );
                return false;
            }
            claves.add(clave);
        }

        const conceptos = new Set<string>();
        for (const fila of valores.tarifas_concepto) {
            if (fila.concepto_id === null) {
                continue;
            }
            if (conceptos.has(fila.concepto_id)) {
                form.setFieldError("tarifas_concepto", "Hay un concepto cargado más de una vez");
                return false;
            }
            conceptos.add(fila.concepto_id);
        }
        return true;
    };

    const guardar = useMutation({
        mutationFn: (valores: Valores) =>
            editandoExistente && detalle !== null
                ? actualizarTarifario(detalle.id, aPayload(valores))
                : crearTarifario(aPayload(valores)),
        onSuccess: (guardado) => {
            void queryClient.invalidateQueries({ queryKey: tarifariosKeys.all });
            notifications.show({
                color: "green",
                message: `Se guardó el tarifario de ${guardado.transportista_razon_social}`,
            });
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
            // business_rule y conflict se muestran en el Alert de acá abajo, no en un toast:
            // el usuario los tiene que poder leer mientras corrige.
            if (error.code === "business_rule" || error.code === "conflict") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({ queryKey: tarifariosKeys.all });
                onClose();
                return;
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const reglaDeNegocio =
        guardar.error?.code === "business_rule" || guardar.error?.code === "conflict"
            ? guardar.error
            : null;

    return (
        <form
            onSubmit={form.onSubmit((valores) => {
                if (sinDuplicados(valores)) {
                    guardar.mutate(valores);
                }
            })}
        >
            <Stack gap="md">
                {enUso && modo === "edicion" && (
                    <Alert color="orange" title="Este tarifario ya se usó para costear">
                        Sus precios quedaron congelados en el costo de al menos una orden de
                        servicio: las filas y la vigencia no se pueden modificar, pero sí podés
                        agregar tarifas nuevas. Para cambiar un precio existente, cerrá su vigencia
                        y duplicalo.
                    </Alert>
                )}

                {reglaDeNegocio && (
                    <Alert color="red" title="No se pudo guardar">
                        {reglaDeNegocio.message}
                    </Alert>
                )}

                <Group grow align="flex-start">
                    <Select
                        label="Transportista"
                        placeholder="Elegí un transportista"
                        searchable
                        allowDeselect={false}
                        data={transportistasData(opciones)}
                        disabled={soloLectura || enUso}
                        {...form.getInputProps("transportista_id")}
                    />
                    <DateTimePicker
                        label="Vigente desde"
                        valueFormat="DD/MM/YYYY HH:mm"
                        disabled={soloLectura || enUso}
                        {...form.getInputProps("vigente_desde")}
                    />
                    <DateTimePicker
                        label="Vigente hasta"
                        placeholder="Sin cierre"
                        valueFormat="DD/MM/YYYY HH:mm"
                        clearable
                        disabled={soloLectura || enUso}
                        {...form.getInputProps("vigente_hasta")}
                    />
                </Group>

                <Fieldset legend={`Tarifas de flete (${form.values.tarifas_flete.length})`}>
                    <FilasTarifaFlete form={form} opciones={opciones} soloLectura={soloLectura} />
                </Fieldset>

                <Fieldset legend={`Conceptos adicionales (${form.values.tarifas_concepto.length})`}>
                    <FilasTarifaConcepto
                        form={form}
                        opciones={opciones}
                        soloLectura={soloLectura}
                    />
                </Fieldset>

                <Group justify="flex-end">
                    <Button variant="default" onClick={onClose}>
                        {soloLectura ? "Cerrar" : "Cancelar"}
                    </Button>
                    {!soloLectura && (
                        <Button type="submit" loading={guardar.isPending}>
                            Guardar
                        </Button>
                    )}
                </Group>
            </Stack>
        </form>
    );
}

function transportistasData(opciones: TarifarioOpcionesOut) {
    return opciones.transportistas.map((t) => ({
        value: String(t.id),
        label: `${t.razon_social} (${t.cuit})`,
    }));
}
