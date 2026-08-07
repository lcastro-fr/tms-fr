import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError, fieldErrors } from "../../../api/errors";
import { aIsoConOffset, formatearFecha } from "../../../lib/date";
import { cerrarTarifario, tarifariosKeys } from "../api";
import type { TarifarioOut } from "../api";

type Props = {
    tarifario: TarifarioOut;
    onClose: () => void;
};

type Valores = { vigente_hasta: string | null };

export function CerrarVigenciaModal({ tarifario, onClose }: Props) {
    const queryClient = useQueryClient();

    const form = useForm<Valores>({
        initialValues: { vigente_hasta: null },
        validate: {
            vigente_hasta: (valor) => (valor ? null : "Ingresá hasta cuándo rige"),
        },
    });

    const cerrar = useMutation({
        mutationFn: (valores: Valores) =>
            cerrarTarifario(tarifario.id, {
                vigente_hasta: aIsoConOffset(valores.vigente_hasta) as string,
            }),
        onSuccess: (cerrado) => {
            void queryClient.invalidateQueries({ queryKey: tarifariosKeys.all });
            notifications.show({
                color: "green",
                message: `El tarifario de ${cerrado.transportista_razon_social} rige hasta ${formatearFecha(cerrado.vigente_hasta)}`,
            });
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
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
        cerrar.error?.code === "business_rule" || cerrar.error?.code === "conflict"
            ? cerrar.error
            : null;

    return (
        <Modal opened onClose={onClose} title="Cerrar la vigencia del tarifario">
            <form onSubmit={form.onSubmit((valores) => cerrar.mutate(valores))}>
                <Stack gap="md">
                    {reglaDeNegocio && (
                        <Alert color="red" title="No se pudo cerrar">
                            {reglaDeNegocio.message}
                        </Alert>
                    )}

                    <Text size="sm">
                        {tarifario.transportista_razon_social}, vigente desde{" "}
                        {formatearFecha(tarifario.vigente_desde)}. A partir del cierre hace falta
                        un tarifario nuevo para poder costear.
                    </Text>

                    <DateTimePicker
                        label="Vigente hasta"
                        valueFormat="DD/MM/YYYY HH:mm"
                        {...form.getInputProps("vigente_hasta")}
                    />

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" loading={cerrar.isPending}>
                            Cerrar vigencia
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}
