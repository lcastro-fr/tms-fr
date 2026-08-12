import { useQueries, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { departamentosQueryOptions, provinciasQueryOptions } from "./api";
import type { DivisionOut, ProvinciaOut, UnionDivisionesIn } from "./api";

export type GrupoProvincia = {
    provincia: ProvinciaOut;
    departamentos: DivisionOut[];
    cargando: boolean;
};

export type Divisiones = {
    provincias: ProvinciaOut[];
    /** El alcance del armado: de estas provincias se listan y se dibujan los departamentos. */
    provinciasElegidas: string[];
    elegirProvincias: (codigos: string[]) => void;
    /** Agrupados, para que la lista no mezcle homónimos de dos provincias. */
    grupos: GrupoProvincia[];
    /** Aplanados, para la capa del mapa. */
    departamentos: DivisionOut[];
    cargandoProvincias: boolean;
    cargandoDepartamentos: boolean;
    fallo: boolean;
    /** Provincias tomadas enteras. */
    provinciasMarcadas: Set<string>;
    departamentosMarcados: Set<string>;
    /** Lo que hay que pintar: incluye los departamentos de una provincia tomada entera. */
    codigosDibujadosMarcados: Set<string>;
    toggleProvincia: (codigo: string) => void;
    toggleDepartamento: (codigo: string) => void;
    limpiar: () => void;
    seleccion: UnionDivisionesIn;
    cantidad: number;
    /** Para los badges: una selección cruza provincias y los nombres vienen de varias queries. */
    nombreDe: (codigo: string) => string;
};

function alternar(previo: Set<string>, codigo: string): Set<string> {
    const siguiente = new Set(previo);
    if (!siguiente.delete(codigo)) {
        siguiente.add(codigo);
    }
    return siguiente;
}

function soloDeProvincias(codigos: Set<string>, provincias: string[]): Set<string> {
    return new Set([...codigos].filter((codigo) => provincias.includes(codigo.slice(0, 2))));
}

export function useDivisiones(): Divisiones {
    const [provinciasElegidas, setProvinciasElegidas] = useState<string[]>([]);
    const [provinciasMarcadas, setProvinciasMarcadas] = useState<Set<string>>(new Set());
    const [departamentosMarcados, setDepartamentosMarcados] = useState<Set<string>>(new Set());

    const queryProvincias = useQuery(provinciasQueryOptions());
    const queriesDepartamentos = useQueries({
        queries: provinciasElegidas.map((codigo) => departamentosQueryOptions(codigo)),
    });

    const provincias = useMemo(() => queryProvincias.data ?? [], [queryProvincias.data]);

    // `useQueries` devuelve un array nuevo por render, así que el memo se ancla en una clave
    // derivada en vez de en su identidad. Es sólida porque los departamentos de una provincia son
    // inmutables: datos del INDEC 2022 con staleTime Infinity.
    const claveDatos = queriesDepartamentos.map((q) => q.data?.length ?? -1).join(",");

    const grupos = useMemo<GrupoProvincia[]>(
        () =>
            provinciasElegidas.flatMap((codigo, indice) => {
                const provincia = provincias.find((p) => p.codigo === codigo);
                if (!provincia) {
                    return [];
                }
                const query = queriesDepartamentos[indice];
                return [
                    {
                        provincia,
                        departamentos: query?.data ?? [],
                        cargando: query?.isPending ?? true,
                    },
                ];
            }),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [provinciasElegidas, provincias, claveDatos],
    );

    const departamentos = useMemo(() => grupos.flatMap((g) => g.departamentos), [grupos]);

    // Sacar una provincia del alcance se lleva sus marcas: si no, quedarían en el payload sin
    // ninguna forma de verlas ni de destildarlas.
    const elegirProvincias = useCallback((codigos: string[]) => {
        setProvinciasElegidas(codigos);
        setProvinciasMarcadas((previo) => soloDeProvincias(previo, codigos));
        setDepartamentosMarcados((previo) => soloDeProvincias(previo, codigos));
    }, []);

    const toggleProvincia = useCallback((codigo: string) => {
        setProvinciasMarcadas((previo) => alternar(previo, codigo));
        // Con la provincia entera marcada, sus departamentos son redundantes en el payload.
        setDepartamentosMarcados(
            (previo) => new Set([...previo].filter((dep) => !dep.startsWith(codigo))),
        );
    }, []);

    const toggleDepartamento = useCallback(
        (codigo: string) => {
            // Con la provincia entera marcada el departamento ya está incluido; sumarlo sería el
            // mismo polígono dos veces. Los checkboxes van disabled, pero el click del mapa
            // también llega acá.
            if (provinciasMarcadas.has(codigo.slice(0, 2))) {
                return;
            }
            setDepartamentosMarcados((previo) => alternar(previo, codigo));
        },
        [provinciasMarcadas],
    );

    const limpiar = useCallback(() => {
        setProvinciasMarcadas(new Set());
        setDepartamentosMarcados(new Set());
    }, []);

    const codigosDibujadosMarcados = useMemo(() => {
        const marcados = new Set(departamentosMarcados);
        for (const departamento of departamentos) {
            if (provinciasMarcadas.has(departamento.codigo.slice(0, 2))) {
                marcados.add(departamento.codigo);
            }
        }
        return marcados;
    }, [departamentos, provinciasMarcadas, departamentosMarcados]);

    const nombres = useRef(new Map<string, string>());
    useEffect(() => {
        for (const division of [...provincias, ...departamentos]) {
            nombres.current.set(division.codigo, division.nombre);
        }
    }, [provincias, departamentos]);
    const nombreDe = useCallback((codigo: string) => nombres.current.get(codigo) ?? codigo, []);

    const seleccion = useMemo(
        () => ({
            provincias: [...provinciasMarcadas],
            departamentos: [...departamentosMarcados],
        }),
        [provinciasMarcadas, departamentosMarcados],
    );

    return {
        provincias,
        provinciasElegidas,
        elegirProvincias,
        grupos,
        departamentos,
        cargandoProvincias: queryProvincias.isPending,
        cargandoDepartamentos: queriesDepartamentos.some((q) => q.isFetching),
        fallo: queryProvincias.isError || queriesDepartamentos.some((q) => q.isError),
        provinciasMarcadas,
        departamentosMarcados,
        codigosDibujadosMarcados,
        toggleProvincia,
        toggleDepartamento,
        limpiar,
        seleccion,
        cantidad: provinciasMarcadas.size + departamentosMarcados.size,
        nombreDe,
    };
}
