import { AppShell, Burger, Group, Menu, NavLink, Text, Title, UnstyledButton } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useQueryClient } from "@tanstack/react-query";
import {
    Link,
    Outlet,
    createFileRoute,
    redirect,
    useNavigate,
    useRouterState,
} from "@tanstack/react-router";

import type { PermisoCodigo } from "../features/auth";
import { logout, meQueryOptions, usePermisos } from "../features/auth";

type ItemDeNav = {
    label: string;
    to: string;
    permiso: PermisoCodigo;
};

const NAV: ItemDeNav[] = [
    { label: "Zonas", to: "/zonas", permiso: "zonas.ver" },
    { label: "Ubicaciones", to: "/ubicaciones", permiso: "ubicaciones.ver" },
    {
        label: "Órdenes de servicio",
        to: "/ordenes-servicio",
        permiso: "ordenes_servicio.ver",
    },
];

function AuthenticatedLayout() {
    const [abierto, { toggle }] = useDisclosure();
    const { sesion, can } = usePermisos();
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const pathname = useRouterState({ select: (s) => s.location.pathname });

    const visibles = NAV.filter((item) => can(item.permiso));

    const cerrarSesion = async () => {
        await logout();
        queryClient.clear();
        await navigate({ to: "/login" });
    };

    return (
        <AppShell
            header={{ height: 56 }}
            navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !abierto } }}
            padding="md"
        >
            <AppShell.Header>
                <Group h="100%" px="md" justify="space-between">
                    <Group gap="sm">
                        <Burger opened={abierto} onClick={toggle} hiddenFrom="sm" size="sm" />
                        <Title order={4}>TMS-FR</Title>
                    </Group>
                    <Menu position="bottom-end">
                        <Menu.Target>
                            <UnstyledButton>
                                <Text size="sm">{sesion.nombre}</Text>
                            </UnstyledButton>
                        </Menu.Target>
                        <Menu.Dropdown>
                            <Menu.Label>{sesion.roles.join(", ") || "Sin roles"}</Menu.Label>
                            <Menu.Item onClick={() => void cerrarSesion()}>Cerrar sesión</Menu.Item>
                        </Menu.Dropdown>
                    </Menu>
                </Group>
            </AppShell.Header>

            <AppShell.Navbar p="xs">
                <NavLink component={Link} to="/" label="Inicio" active={pathname === "/"} />
                {visibles.map((item) => (
                    <NavLink
                        key={item.to}
                        component={Link}
                        to={item.to}
                        label={item.label}
                        active={pathname.startsWith(item.to)}
                    />
                ))}
            </AppShell.Navbar>

            <AppShell.Main>
                <Outlet />
            </AppShell.Main>
        </AppShell>
    );
}

export const Route = createFileRoute("/_authenticated")({
    beforeLoad: async ({ context, location }) => {
        const sesion = await context.queryClient
            .ensureQueryData(meQueryOptions())
            .catch(() => null);

        if (!sesion) {
            throw redirect({ to: "/login", search: { next: location.href } });
        }
        return { sesion };
    },
    component: AuthenticatedLayout,
});
