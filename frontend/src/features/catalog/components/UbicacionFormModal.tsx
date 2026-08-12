import {
    Alert,
    Button,
    Fieldset,
    Group,
    Input,
    Modal,
    NumberInput,
    Select,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import {
    useMutation,
    useQueryClient,
    useSuspenseQuery,
} from "@tanstack/react-query";
import { useMemo, useState } from "react";
import type { ClipboardEvent } from "react";

import { ApiError, fieldErrors } from "../../../api/errors";
import { CentrarEn } from "../../../components/CentrarEn";
import { MapaBase } from "../../../components/MapaBase";
import { SelectorPunto } from "../../../components/SelectorPunto";
import {
    aLatLng,
    aPunto,
    parsearParLatLng,
    redondearCoordenada,
} from "../../../lib/geojson";
import type { LatLng } from "../../../lib/geojson";
import { usePermisos } from "../../auth";
import {
    actualizarUbicacion,
    crearUbicacion,
    geocodificarUbicacion,
    ubicacionesKeys,
    ubicacionesOpcionesQueryOptions,
} from "../api";
import type {
    TipoUbicacion,
    UbicacionCrearIn,
    UbicacionIn,
    UbicacionOut,
} from "../api";
import { useUbicaciones } from "../use-ubicaciones";
import { CapaUbicaciones } from "./CapaUbicaciones";
import { ControlUbicaciones } from "./ControlUbicaciones";

type Props = {
    ubicacion: UbicacionOut | null;
    onClose: () => void;
    onCreada?: () => void;
    onGuardada?: (guardada: UbicacionOut) => void;
};

type Valores = {
    nombre: string;
    tipo: TipoUbicacion;
    codigo: string;
    calle: string;
    localidad: string;
    provincia: string;
    pais_codigo: string;
    lat: number | string;
    lng: number | string;
};

const validarCoordenada = (
    valor: number | string,
    maximo: number,
    faltante: string,
) => {
    if (valor === "") {
        return faltante;
    }
    const numero = Number(valor);
    if (!Number.isFinite(numero)) {
        return "No es un número";
    }
    if (Math.abs(numero) > maximo) {
        return `Tiene que estar entre -${maximo} y ${maximo}`;
    }
    return null;
};

export function UbicacionFormModal({
    ubicacion,
    onClose,
    onCreada,
    onGuardada,
}: Props) {
    const queryClient = useQueryClient();
    const { canAlguno } = usePermisos();
    const { data: opciones } = useSuspenseQuery(
        ubicacionesOpcionesQueryOptions(),
    );
    const esNuevo = ubicacion === null;
    const [latInicial, lngInicial] = ubicacion?.coordinates
        ? aLatLng(ubicacion.coordinates)
        : ["" as const, "" as const];

    const form = useForm<Valores>({
        initialValues: {
            nombre: ubicacion?.nombre ?? "",
            tipo: (ubicacion?.tipo as TipoUbicacion) ?? "cliente",
            codigo: ubicacion?.codigo ?? "",
            calle: ubicacion?.calle ?? "",
            localidad: ubicacion?.localidad ?? "",
            provincia: ubicacion?.provincia ?? "",
            pais_codigo: ubicacion?.pais_codigo ?? "AR",
            lat: latInicial,
            lng: lngInicial,
        },
        validate: {
            nombre: (valor) => (valor.trim() ? null : "Ingresá un nombre"),
            lat: (valor) =>
                validarCoordenada(
                    valor,
                    90,
                    "Escribí la latitud o marcá el punto en el mapa",
                ),
            lng: (valor) =>
                validarCoordenada(
                    valor,
                    180,
                    "Escribí la longitud o marcá el punto en el mapa",
                ),
            calle: (valor) =>
                !esNuevo || valor.trim() ? null : "Ingresá la calle",
            localidad: (valor) =>
                !esNuevo || valor.trim() ? null : "Ingresá la localidad",
            provincia: (valor) =>
                !esNuevo || valor.trim() ? null : "Ingresá la provincia",
            codigo: (valor, valores) =>
                esNuevo && valores.tipo === "planta" && !valor.trim()
                    ? "Una planta necesita código para que la ingesta la encuentre"
                    : null,
        },
    });

    const [centro] = useState(() =>
        ubicacion?.coordinates ? aLatLng(ubicacion.coordinates) : undefined,
    );
    const [aCentrar, setACentrar] = useState<LatLng | null>(null);
    const esPlanta = form.values.tipo === "planta";

    const { lat, lng } = form.values;
    // A medio tipear NumberInput entrega "-" o "": un NaN acá llega a Leaflet como posición.
    const punto = useMemo(() => {
        const numeroLat = lat === "" ? NaN : Number(lat);
        const numeroLng = lng === "" ? NaN : Number(lng);
        return Number.isFinite(numeroLat) && Number.isFinite(numeroLng)
            ? aPunto(numeroLat, numeroLng)
            : null;
    }, [lat, lng]);

    const escribirCoordenada = (punto: LatLng) => {
        form.setFieldValue("lat", redondearCoordenada(punto[0]));
        form.setFieldValue("lng", redondearCoordenada(punto[1]));
    };

    const ubicaciones = useUbicaciones();
    const vecinas = useMemo(
        () => ubicaciones.dibujables.filter((u) => u.id !== ubicacion?.id),
        [ubicaciones.dibujables, ubicacion?.id],
    );

    const tipos = opciones.tipos_ubicacion.map((o) => ({
        value: o.value,
        label: o.label,
    }));
    const paises = opciones.paises.map((p) => ({
        value: p.codigo,
        label: p.nombre,
    }));

    const guardar = useMutation({
        mutationFn: (valores: Valores) => {
            const lat = Number(valores.lat);
            const lng = Number(valores.lng);
            if (
                valores.lat === "" ||
                valores.lng === "" ||
                !Number.isFinite(lat) ||
                !Number.isFinite(lng)
            ) {
                throw new Error(
                    "Sin coordenada: el validate tendría que haberlo frenado",
                );
            }
            const coordinates = aPunto(lat, lng);
            if (ubicacion) {
                const payload: UbicacionIn = {
                    nombre: valores.nombre.trim(),
                    tipo: valores.tipo,
                    localidad: valores.localidad.trim(),
                    provincia: valores.provincia.trim(),
                    calle: valores.calle.trim(),
                    coordinates,
                };
                return actualizarUbicacion(ubicacion.id, payload);
            }
            const payload: UbicacionCrearIn = {
                nombre: valores.nombre.trim(),
                tipo: valores.tipo,
                codigo: valores.codigo.trim() || null,
                calle: valores.calle.trim(),
                localidad: valores.localidad.trim(),
                provincia: valores.provincia.trim(),
                pais_codigo: valores.pais_codigo,
                coordinates,
            };
            return crearUbicacion(payload);
        },
        onSuccess: (guardada) => {
            void queryClient.invalidateQueries({
                queryKey: ubicacionesKeys.all,
            });
            notifications.show({
                color: "green",
                message: esNuevo
                    ? `Se creó la ubicación ${guardada.nombre}`
                    : `Se validó la ubicación ${guardada.nombre}`,
            });
            if (esNuevo) {
                onCreada?.();
            }
            onGuardada?.(guardada);
            onClose();
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
                return;
            }
            if (error.code === "conflict") {
                form.setErrors({ codigo: error.message });
                return;
            }
            if (error.code === "business_rule") {
                return;
            }
            if (error.code === "not_found") {
                void queryClient.invalidateQueries({
                    queryKey: ubicacionesKeys.all,
                });
                onClose();
            }
            notifications.show({ color: "red", message: error.message });
        },
    });

    const geocodificar = useMutation({
        mutationFn: () =>
            geocodificarUbicacion({
                calle: form.values.calle.trim() || null,
                localidad: form.values.localidad.trim() || null,
                provincia: form.values.provincia.trim() || null,
                pais_codigo: form.values.pais_codigo,
            }),
        onSuccess: (encontrada) => {
            const geocodificado = aLatLng(encontrada.coordinates);
            escribirCoordenada(geocodificado);
            setACentrar(geocodificado);
        },
        onError: (error: ApiError) => {
            const campos = fieldErrors(error);
            if (Object.keys(campos).length > 0) {
                form.setErrors(campos);
            }
        },
    });

    const reglaDeNegocio =
        guardar.error?.code === "business_rule" ? guardar.error : null;
    const puedeGeocodificar = canAlguno(
        "ubicaciones.crear",
        "ubicaciones.editar",
    );
    const hayDireccion = Boolean(
        form.values.calle.trim() ||
        form.values.localidad.trim() ||
        form.values.provincia.trim(),
    );

    const propsLat = form.getInputProps("lat");
    const propsLng = form.getInputProps("lng");

    // El par que copia Google Maps entra de una: sin esto la coma corta el NumberInput.
    const pegarPar = (evento: ClipboardEvent<HTMLInputElement>) => {
        const par = parsearParLatLng(evento.clipboardData.getData("text"));
        if (!par) {
            return;
        }
        evento.preventDefault();
        escribirCoordenada(par);
        setACentrar(par);
    };

    const centrarEnLoTipeado = () => {
        if (punto) {
            setACentrar(aLatLng(punto));
        }
    };

    return (
        <Modal
            opened
            onClose={onClose}
            size="70rem"
            title={
                esNuevo
                    ? "Nueva ubicación"
                    : ubicacion.codigo
                      ? `${ubicacion.nombre} (${ubicacion.codigo})`
                      : ubicacion.nombre
            }
            closeOnEscape={false}
            closeOnClickOutside={false}
        >
            <form
                onSubmit={form.onSubmit((valores) => guardar.mutate(valores))}
            >
                <Stack gap="md">
                    {reglaDeNegocio && (
                        <Alert color="red" title="No se pudo guardar">
                            {reglaDeNegocio.message}
                        </Alert>
                    )}

                    {esPlanta && (
                        <Alert color="yellow" title="Es una planta">
                            {esNuevo
                                ? "La ingesta de SAP busca las plantas por código, así que necesita uno para poder usarla como origen."
                                : "Cambiarle el tipo hace que la ingesta de SAP rechace los tickets que la usan como planta de origen."}
                        </Alert>
                    )}

                    <Group grow align="flex-start">
                        <TextInput
                            label="Nombre"
                            maxLength={120}
                            {...form.getInputProps("nombre")}
                        />
                        <Select
                            label="Tipo"
                            data={tipos}
                            allowDeselect={false}
                            {...form.getInputProps("tipo")}
                        />
                        {esNuevo ? (
                            <TextInput
                                label="Código"
                                placeholder="Opcional"
                                maxLength={20}
                                {...form.getInputProps("codigo")}
                            />
                        ) : (
                            <TextInput
                                label="Código"
                                value={ubicacion.codigo ?? ""}
                                readOnly
                            />
                        )}
                    </Group>

                    <Fieldset legend="Dirección de referencia">
                        <Stack gap="xs">
                            <TextInput
                                label="Calle"
                                maxLength={200}
                                //readOnly={!esNuevo}
                                {...form.getInputProps("calle")}
                            />
                            <Group grow align="flex-start">
                                <TextInput
                                    label="Localidad"
                                    maxLength={120}
                                    //readOnly={!esNuevo}
                                    {...form.getInputProps("localidad")}
                                />
                                <TextInput
                                    label="Provincia"
                                    maxLength={120}
                                    //readOnly={!esNuevo}
                                    {...form.getInputProps("provincia")}
                                />
                                {esNuevo ? (
                                    <Select
                                        label="País"
                                        data={paises}
                                        allowDeselect={false}
                                        searchable
                                        {...form.getInputProps("pais_codigo")}
                                    />
                                ) : (
                                    <TextInput
                                        label="País"
                                        value={ubicacion.pais ?? ""}
                                        readOnly
                                    />
                                )}
                            </Group>

                            {geocodificar.isError && (
                                <Alert
                                    color="yellow"
                                    title="No se pudo geolocalizar"
                                >
                                    {geocodificar.error.message} Marcá el punto
                                    en el mapa.
                                </Alert>
                            )}
                            {geocodificar.data && (
                                <Text size="xs" c="dimmed">
                                    Se buscó: {geocodificar.data.consulta}
                                </Text>
                            )}

                            {puedeGeocodificar && (
                                <Group justify="flex-end">
                                    <Button
                                        size="xs"
                                        variant="light"
                                        disabled={!hayDireccion}
                                        loading={geocodificar.isPending}
                                        onClick={() => geocodificar.mutate()}
                                    >
                                        Geolocalizar
                                    </Button>
                                </Group>
                            )}
                        </Stack>
                    </Fieldset>

                    <div>
                        <Input.Label>Coordenada</Input.Label>
                        <Text size="xs" c="dimmed" mb="xs">
                            Escribí la coordenada, clickeá el mapa o arrastrá el
                            marcador.
                            {esNuevo
                                ? " La ubicación se guarda validada."
                                : " Al guardar, la ubicación queda validada."}
                        </Text>
                        <Group grow align="flex-start" mb="xs">
                            <NumberInput
                                label="Latitud"
                                placeholder="-34.603722"
                                decimalScale={6}
                                hideControls
                                {...propsLat}
                                onPaste={pegarPar}
                                onBlur={(evento) => {
                                    propsLat.onBlur?.(evento);
                                    centrarEnLoTipeado();
                                }}
                            />
                            <NumberInput
                                label="Longitud"
                                placeholder="-58.381592"
                                decimalScale={6}
                                hideControls
                                {...propsLng}
                                onPaste={pegarPar}
                                onBlur={(evento) => {
                                    propsLng.onBlur?.(evento);
                                    centrarEnLoTipeado();
                                }}
                            />
                        </Group>
                        <Group mb="xs">
                            <ControlUbicaciones
                                puedeVer={ubicaciones.puedeVer}
                                mostrar={ubicaciones.mostrar}
                                onMostrar={ubicaciones.setMostrar}
                                cargando={ubicaciones.cargando}
                                fallo={ubicaciones.fallo}
                                sinCoordenadas={ubicaciones.sinCoordenadas}
                            />
                        </Group>
                        <MapaBase center={centro} zoom={centro ? 14 : 4}>
                            <SelectorPunto
                                valor={punto}
                                onChange={(elegido) =>
                                    escribirCoordenada(aLatLng(elegido))
                                }
                            />
                            {/* MapContainer sólo honra center al montar. */}
                            <CentrarEn punto={aCentrar} />
                            {ubicaciones.mostrar && (
                                <CapaUbicaciones ubicaciones={vecinas} />
                            )}
                        </MapaBase>
                        {form.errors.coordinates && (
                            <Input.Error mt="xs">
                                {form.errors.coordinates}
                            </Input.Error>
                        )}
                    </div>

                    <Group justify="flex-end">
                        <Button variant="default" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" loading={guardar.isPending}>
                            {esNuevo ? "Crear" : "Guardar y validar"}
                        </Button>
                    </Group>
                </Stack>
            </form>
        </Modal>
    );
}
