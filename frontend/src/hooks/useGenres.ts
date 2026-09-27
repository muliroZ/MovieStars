import { useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { listGenres } from '../api/movies'

export interface GenresState {
  status: 'loading' | 'error' | 'success'
  genres: string[]
  message: string | null
  retry: () => void
}

/**
 * Lista de gêneros cadastrados (GET /genres). Usada pelo GenrePicker e pelo catálogo,
 * que precisa da lista mesmo com o painel de filtros fechado (plan 100, DEC-11).
 */
export function useGenres(): GenresState {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{
    attempt: number
    genres: string[] | null
    message: string | null
  } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listGenres(controller.signal)
      .then((genres) => setResult({ attempt, genres, message: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setResult({ attempt, genres: null, message: errorMessage(error, 'Erro ao carregar os gêneros.') })
      })
    return () => controller.abort()
  }, [attempt])

  const current = result?.attempt === attempt ? result : null
  return {
    status: current === null ? 'loading' : current.genres === null ? 'error' : 'success',
    genres: current?.genres ?? [],
    message: current?.message ?? null,
    retry: () => setAttempt((value) => value + 1),
  }
}
