import { Alert, Center, Stack, Text } from "@mantine/core";
import { createFileRoute, redirect } from "@tanstack/react-router";

import { usePermisos } from "../../features/auth";

// Es el aterrizaje de requirePermiso, que hace redirect({ to: "/" }): si esta ruta
// redirigiera siempre, un usuario sin permisos rebotaría entre las dos para siempre.
function SinAcceso() {
    const { sesion } = usePermisos();

    return (
        <Center mih="60vh">
            <Alert
                variant="outline"
                color="yellow"
                title="No tenés acceso a ninguna pantalla"
                maw={520}
            >
                <Stack gap="xs">
                    <Text size="sm">
                        Tu usuario ({sesion.email}) no tiene ningún permiso
                        asignado.
                    </Text>
                    <Text size="sm">
                        Pedile a un administrador que te asigne un rol.
                    </Text>
                </Stack>
            </Alert>
        </Center>
    );
}

export const Route = createFileRoute("/_authenticated/")({
    // La cascada sigue el orden de NAV. Los destinos van literales y no derivados del
    // manifiesto para que cada redirect quede tipado contra su ruta.
    beforeLoad: ({ context }) => {
        const { permisos } = context.sesion;

        if (permisos.includes("ordenes_servicio.ver")) {
            throw redirect({ to: "/ordenes-servicio" });
        }
        if (permisos.includes("zonas.ver")) {
            throw redirect({ to: "/zonas" });
        }
        if (permisos.includes("ubicaciones.ver")) {
            throw redirect({ to: "/ubicaciones" });
        }
        if (permisos.includes("tarifarios.ver")) {
            throw redirect({ to: "/tarifarios" });
        }
    },
    component: SinAcceso,
});
