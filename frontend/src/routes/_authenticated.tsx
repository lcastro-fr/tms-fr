import {
    AppShell,
    Avatar,
    Box,
    Burger,
    Group,
    Menu,
    NavLink,
    Text,
    UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { CaretDown } from "@phosphor-icons/react/CaretDown";
import { SignOut } from "@phosphor-icons/react/SignOut";
import { useQueryClient } from "@tanstack/react-query";
import {
    Link,
    Outlet,
    createFileRoute,
    redirect,
    useNavigate,
    useRouterState,
} from "@tanstack/react-router";

import { GRUPOS, NAV } from "../app/navegacion";
import { ColorSchemeToggle } from "../components/ColorSchemeToggle";
import { logout, meQueryOptions, usePermisos } from "../features/auth";
import classes from "./_authenticated.module.css";

function iniciales(nombre: string, email: string): string {
    const partes = nombre.trim().split(/\s+/).filter(Boolean);
    if (partes.length === 0) return email.slice(0, 2).toUpperCase();
    return partes
        .slice(0, 2)
        .map((parte) => parte[0])
        .join("")
        .toUpperCase();
}

function AuthenticatedLayout() {
    const [abierto, { toggle, close }] = useDisclosure();
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
        <>
            {/* Primero en el DOM a propósito: si no, no se llega antes que a la navbar. */}
            <a href="#contenido" className={classes.saltar}>
                Ir al contenido
            </a>

            <AppShell
                header={{ height: 60 }}
                navbar={{
                    width: 240,
                    breakpoint: "sm",
                    collapsed: { mobile: !abierto },
                }}
                padding="md"
            >
                <AppShell.Header>
                    <Group h="100%" justify="space-between" wrap="nowrap">
                        <Group gap={0} wrap="nowrap">
                            <Burger
                                opened={abierto}
                                onClick={toggle}
                                hiddenFrom="sm"
                                size="sm"
                                ml="xs"
                            />
                            <Link to="/" className={classes.marca}>
                                <Text className={classes.nombre}>Fletes</Text>
                                <Text
                                    size="10px"
                                    c="dimmed"
                                    fw={600}
                                    tt="uppercase"
                                    lts="0.08em"
                                >
                                    TMS
                                </Text>
                            </Link>
                        </Group>

                        <Group gap="sm" pr="md" wrap="nowrap">
                            <ColorSchemeToggle />
                            <Menu position="bottom-end" width={240}>
                                <Menu.Target>
                                    <UnstyledButton className={classes.usuario}>
                                        <Avatar
                                            color="gold"
                                            size={28}
                                            radius="xl"
                                        >
                                            {iniciales(
                                                sesion.nombre,
                                                sesion.email,
                                            )}
                                        </Avatar>
                                        <Text size="sm" visibleFrom="xs">
                                            {sesion.nombre || sesion.email}
                                        </Text>
                                        <CaretDown size={12} />
                                    </UnstyledButton>
                                </Menu.Target>
                                <Menu.Dropdown>
                                    <Menu.Label>
                                        <Text size="xs" truncate>
                                            {sesion.email}
                                        </Text>
                                    </Menu.Label>
                                    <Menu.Divider />
                                    <Menu.Item
                                        color="red"
                                        leftSection={<SignOut size={16} />}
                                        onClick={() => void cerrarSesion()}
                                    >
                                        Cerrar sesión
                                    </Menu.Item>
                                </Menu.Dropdown>
                            </Menu>
                        </Group>
                    </Group>
                </AppShell.Header>

                <AppShell.Navbar p="xs">
                    {GRUPOS.map((grupo) => {
                        const items = visibles.filter(
                            (item) => item.grupo === grupo.id,
                        );
                        if (items.length === 0) return null;

                        return (
                            <Box key={grupo.id} mb="sm">
                                <Text
                                    className={classes.seccion}
                                    c="dimmed"
                                    mb={4}
                                >
                                    {grupo.label}
                                </Text>
                                {items.map((item) => (
                                    <NavLink
                                        key={item.to}
                                        component={Link}
                                        to={item.to}
                                        label={item.label}
                                        leftSection={<item.Icono size={18} />}
                                        active={pathname.startsWith(item.to)}
                                        className={classes.item}
                                        onClick={close}
                                    />
                                ))}
                            </Box>
                        );
                    })}
                </AppShell.Navbar>

                <AppShell.Main id="contenido">
                    <Outlet />
                </AppShell.Main>
            </AppShell>
        </>
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
