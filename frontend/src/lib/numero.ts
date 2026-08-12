const ENTERO = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const CHICO = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

/**
 * La superficie de una zona, que el backend manda como string igual que cualquier Decimal.
 */
export function formatearKm2(valor: string | null, vacio = "—"): string {
    // Number("") es 0, no NaN: sin este guard una superficie ausente se muestra como 0 km².
    if (valor === null || valor.trim() === "") {
        return vacio;
    }
    const numero = Number(valor);
    if (!Number.isFinite(numero)) {
        return vacio;
    }
    // Una zona chica redondeada a entero se leería como 0 km², que es el número equivocado.
    return (numero < 100 ? CHICO : ENTERO).format(numero);
}
