import { useEffect, useState } from 'react'

import { ApiError, errorMessage } from '../api/client'
import { getMovie } from '../api/movies'
import type { MovieDetail } from '../types/movie'

export type MovieState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'not-found' }
  | { status: 'success'; data: MovieDetail }

interface MovieActions {
  /** Busca de novo passando por "carregando" (telas de erro). */
  retry: () => void
  /** Busca de novo mantendo os dados atuais na tela até a resposta (spec 004, DEC-5). */
  refresh: () => void
}

/** Busca os detalhes de um filme; 404 vira o estado `not-found`. */
export function useMovie(skMovieId: string): MovieState & MovieActions {
  const [attempt, setAttempt] = useState(0)
  // Mesmo padrão do useMovies: o resultado guarda a requisição a que pertence.
  const requestKey = `${skMovieId}|${attempt}`
  const [result, setResult] = useState<{ key: string; state: MovieState } | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    getMovie(skMovieId, controller.signal)
      .then((data) => setResult({ key: requestKey, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const state: MovieState =
          error instanceof ApiError && error.status === 404
            ? { status: 'not-found' }
            : { status: 'error', message: errorMessage(error, 'Erro inesperado ao carregar o filme.') }
        setResult({ key: requestKey, state })
      })

    return () => controller.abort()
  }, [skMovieId, requestKey])

  const state: MovieState = result?.key === requestKey ? result.state : { status: 'loading' }

  function refresh() {
    // Grava com a chave atual: se o usuário trocar de filme antes da resposta, ela é ignorada.
    getMovie(skMovieId)
      .then((data) => setResult({ key: requestKey, state: { status: 'success', data } }))
      .catch(() => {
        // Falhou: os dados que já estão na tela continuam.
      })
  }

  return { ...state, retry: () => setAttempt((current) => current + 1), refresh }
}
