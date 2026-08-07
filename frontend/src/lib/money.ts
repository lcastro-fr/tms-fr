const PESOS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
});

/**
 * Los Decimal del backend viajan como string. Este es el único lugar del frontend que los
 * pasa por Number(), y sólo para mostrarlos: nunca se hace aritmética de pesos en float.
 */
export function formatearPesos(valor: string | null, vacio = "—"): string {
    // Number("") es 0, no NaN: sin este guard un precio ausente se muestra como $ 0,00.
    if (valor === null || valor.trim() === "") {
        return vacio;
    }
    const numero = Number(valor);
    return Number.isFinite(numero) ? PESOS.format(numero) : vacio;
}
