import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'
import { listMovies } from '../api/movies'
import type { MovieListItem, Page } from '../types/movie'

export type MoviesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; data: Page<MovieListItem> }

/** Busca uma página do catálogo e informa se está carregando, com erro ou pronta. */
export function useMovies(page: number, search: string): MoviesState & { retry: () => void } {
  const [attempt, setAttempt] = useState(0)
  // Cada resultado guarda a requisição a que pertence. Enquanto o resultado atual
  // não chega, o estado é "loading", sem precisar de setState síncrono no efeito.
  const requestKey = `${page}|${search}|${attempt}`
  const [result, setResult] = useState<{ key: string; state: MoviesState } | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    listMovies({ page, search }, controller.signal)
      .then((data) => setResult({ key: requestKey, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return // trocou de página/busca: resposta velha
        const message =
          error instanceof ApiError ? error.message : 'Erro inesperado ao carregar os filmes.'
        setResult({ key: requestKey, state: { status: 'error', message } })
      })

    // Cancela a requisição anterior quando página ou busca mudam antes de ela terminar.
    return () => controller.abort()
  }, [page, search, requestKey])

  const state: MoviesState =
    result?.key === requestKey ? result.state : { status: 'loading' }
  return { ...state, retry: () => setAttempt((current) => current + 1) }
}
