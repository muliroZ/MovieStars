import { useEffect, useState } from 'react'

import { errorMessage, type QueryParams } from '../api/client'
import { listMovies } from '../api/movies'
import type { MovieListItem, Page } from '../types/movie'
import { type CatalogFilters, DEFAULT_FILTERS, filtersToApiParams } from '../utils/catalogFilters'

export type MoviesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: Page<MovieListItem> }

/** Busca uma página do catálogo e informa se está carregando, com erro ou pronta. */
export function useMovies(
  page: number,
  search: string,
  filters: CatalogFilters = DEFAULT_FILTERS,
): MoviesState & { retry: () => void } {
  const [attempt, setAttempt] = useState(0)
  // Os filtros viram texto: o objeto é recriado a cada renderização, o texto só muda
  // quando algum filtro muda de verdade (senão o efeito rodaria sem parar).
  const filtersKey = JSON.stringify(filtersToApiParams(filters))
  // Cada resultado guarda a requisição a que pertence. Enquanto o resultado atual
  // não chega, o estado é "loading", sem precisar de setState síncrono no efeito.
  const requestKey = `${page}|${search}|${filtersKey}|${attempt}`
  const [result, setResult] = useState<{ key: string; state: MoviesState } | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    const filterParams = JSON.parse(filtersKey) as QueryParams
    listMovies({ page, search, filterParams }, controller.signal)
      .then((data) => setResult({ key: requestKey, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return // trocou de página/busca: resposta velha
        const message = errorMessage(error, 'Erro inesperado ao carregar os filmes.')
        setResult({ key: requestKey, state: { status: 'error', message } })
      })

    // Cancela a requisição anterior quando página, busca ou filtros mudam antes de ela terminar.
    return () => controller.abort()
  }, [page, search, filtersKey, requestKey])

  const state: MoviesState =
    result?.key === requestKey ? result.state : { status: 'loading' }
  return { ...state, retry: () => setAttempt((current) => current + 1) }
}
