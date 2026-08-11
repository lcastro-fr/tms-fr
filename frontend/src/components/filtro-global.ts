import type { FilterFn } from "@tanstack/react-table";

import { normalizarTexto } from "../lib/texto";

/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
export const filtroGlobalTexto: FilterFn<any> = (
    row,
    columnId,
    aguja: string,
) => normalizarTexto(String(row.getValue(columnId) ?? "")).includes(aguja);

filtroGlobalTexto.resolveFilterValue = (valor) =>
    normalizarTexto(String(valor ?? ""));
