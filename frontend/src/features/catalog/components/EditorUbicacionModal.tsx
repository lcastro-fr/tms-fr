import { Loader } from "@mantine/core";
import { useSuspenseQuery } from "@tanstack/react-query";
import { Suspense, lazy } from "react";

import { ubicacionQueryOptions } from "../api";
import type { UbicacionOut } from "../api";

// El import es dinámico para que Leaflet y geoman no entren al chunk del barrel.
const UbicacionFormModal = lazy(() =>
    import("./UbicacionFormModal").then((m) => ({ default: m.UbicacionFormModal })),
);

type Props = {
    ubicacionId: number;
    onClose: () => void;
    onGuardada?: (guardada: UbicacionOut) => void;
};

function Cargador({ ubicacionId, onClose, onGuardada }: Props) {
    const { data: ubicacion } = useSuspenseQuery(ubicacionQueryOptions(ubicacionId));

    return (
        <UbicacionFormModal ubicacion={ubicacion} onClose={onClose} onGuardada={onGuardada} />
    );
}

/** Abre el formulario de ubicación desde un id, para pantallas que sólo tienen eso. */
export function EditorUbicacionModal(props: Props) {
    return (
        <Suspense fallback={<Loader size="sm" />}>
            <Cargador {...props} />
        </Suspense>
    );
}
