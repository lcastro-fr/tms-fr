const PESOS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
});

/**
 * Los Decimal del backend viajan como string. Este es el único lugar del frontend que los
 * pasa por Number(), y sólo para mostrarlos: nunca se hace aritmética de pesos en float.
 */
function aNumero(valor: string | null): number | null {
    // Number("") es 0, no NaN: sin este guard un precio ausente se muestra como $ 0,00.
    if (valor === null || valor.trim() === "") {
        return null;
    }
    const numero = Number(valor);
    return Number.isFinite(numero) ? numero : null;
}

export function formatearPesos(valor: string | null, vacio = "—"): string {
    const numero = aNumero(valor);
    return numero === null ? vacio : PESOS.format(numero);
}

/**
 * El desvío entre dos importes, con signo y ya formateado. Devuelve null cuando falta
 * alguno de los dos o cuando no hay desvío: sólo se muestra si hay algo que mostrar.
 */
export function diferenciaPesos(
    valor: string | null,
    contra: string | null,
): string | null {
    const a = aNumero(valor);
    const b = aNumero(contra);
    if (a === null || b === null) {
        return null;
    }
    // Los centavos se redondean: la resta en float deja colas de 1e-10 que se ven como desvío.
    const delta = Math.round((a - b) * 100) / 100;
    if (delta === 0) {
        return null;
    }
    return `${delta > 0 ? "+" : "-"}${PESOS.format(Math.abs(delta))}`;
}
