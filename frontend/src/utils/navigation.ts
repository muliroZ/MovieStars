/**
 * Estado de navegação "de onde vim no catálogo" (spec 002, CA-23).
 *
 * O cartão do catálogo passa `{ catalogSearch: "?search=...&page=..." }`; detalhes e
 * formulário repassam esse estado para o "Voltar ao catálogo" continuar funcionando.
 */

export interface CatalogState {
  catalogSearch: string
}

/** Lê o `catalogSearch` do estado da navegação (ou "" se a página foi aberta direto). */
export function catalogSearchFrom(state: unknown): string {
  if (
    typeof state === 'object' &&
    state !== null &&
    'catalogSearch' in state &&
    typeof state.catalogSearch === 'string'
  ) {
    return state.catalogSearch
  }
  return ''
}

/** Endereço do catálogo de onde o usuário veio, ou `/` se abriu o endereço direto. */
export function catalogPath(state: unknown): string {
  return `/${catalogSearchFrom(state)}`
}
