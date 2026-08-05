import { Alert, Button, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMutation } from "@tanstack/react-query";

import { ApiError, fieldErrors } from "../../../api/errors";
import { bootstrapCsrf, login } from "../api";
import type { LoginIn, SesionOut } from "../api";

type Props = {
    onSuccess: (sesion: SesionOut) => void;
};

export function LoginForm({ onSuccess }: Props) {
    const form = useForm<LoginIn>({
        initialValues: { email: "", password: "" },
        validate: {
            email: (value) => (value.trim() ? null : "Ingresá tu email"),
            password: (value) => (value ? null : "Ingresá tu contraseña"),
        },
    });

    const mutation = useMutation({
        mutationFn: async (values: LoginIn) => {
            try {
                return await login(values);
            } catch (error) {
                if (error instanceof ApiError && error.code === "forbidden") {
                    await bootstrapCsrf();
                    return await login(values);
                }
                throw error;
            }
        },
        onSuccess,
        onError: (error: ApiError) => form.setErrors(fieldErrors(error)),
    });

    const mensaje =
        mutation.error && Object.keys(fieldErrors(mutation.error)).length === 0
            ? mutation.error.message
            : null;

    return (
        <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
            <Stack gap="md">
                {mensaje && (
                    <Alert color="red" title="No se pudo iniciar sesión">
                        {mensaje}
                    </Alert>
                )}
                <TextInput
                    label="Email"
                    type="email"
                    autoComplete="username"
                    {...form.getInputProps("email")}
                />
                <PasswordInput
                    label="Contraseña"
                    autoComplete="current-password"
                    {...form.getInputProps("password")}
                />
                <Button type="submit" loading={mutation.isPending}>
                    Entrar
                </Button>
            </Stack>
        </form>
    );
}
