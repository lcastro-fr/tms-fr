/**
 * Normaliza texto para comparar lo que alguien tipea contra lo que trae la base: sin
 * diacríticos y en minúsculas, así "cordoba" encuentra "Córdoba".
 */
export function normalizarTexto(valor: string): string {
    // La ñ también pierde la tilde y queda "n": nadie tipea "ñ" para buscar "Ñandú".
    return valor
        .normalize("NFD")
        .replace(/\p{Diacritic}/gu, "")
        .toLowerCase();
}
