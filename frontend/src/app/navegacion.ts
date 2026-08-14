import { ClipboardText } from "@phosphor-icons/react/ClipboardText";
import { CurrencyDollar } from "@phosphor-icons/react/CurrencyDollar";
import { MapPin } from "@phosphor-icons/react/MapPin";
import { Polygon } from "@phosphor-icons/react/Polygon";

import type { PermisoCodigo } from "../features/auth";

type Icono = typeof ClipboardText;

export type GrupoNav = "operacion" | "maestros";

export type ItemDeNav = {
    label: string;
    to: string;
    permiso: PermisoCodigo;
    grupo: GrupoNav;
    Icono: Icono;
};

export const GRUPOS: { id: GrupoNav; label: string }[] = [
    { id: "operacion", label: "Operación" },
    { id: "maestros", label: "Datos maestros" },
];

// El orden es también el de la cascada de _authenticated/index.tsx.
export const NAV: ItemDeNav[] = [
    {
        label: "Órdenes de servicio",
        to: "/ordenes-servicio",
        permiso: "ordenes_servicio.ver",
        grupo: "operacion",
        Icono: ClipboardText,
    },
    {
        label: "Zonas",
        to: "/zonas",
        permiso: "zonas.ver",
        grupo: "maestros",
        Icono: Polygon,
    },
    {
        label: "Ubicaciones",
        to: "/ubicaciones",
        permiso: "ubicaciones.ver",
        grupo: "maestros",
        Icono: MapPin,
    },
    {
        label: "Tarifarios",
        to: "/tarifarios",
        permiso: "tarifarios.ver",
        grupo: "maestros",
        Icono: CurrencyDollar,
    },
];
