import { useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { listMovieReviews } from '../api/movies'
import type { Review } from '../types/movie'

interface LoadedReviews {
  key: string
  items: Review[]
  total: number
  page: number // última página carregada
  pages: number
}

export interface ReviewsResult {
  status: 'loading' | 'error' | 'success'
  message: string | null
  items: Review[]
  total: number
  hasMore: boolean
  loadingMore: boolean
  loadMoreError: string | null
  retry: () => void
  loadMore: () => void
}

/** Avaliações de um filme: primeira página ao abrir e "mostrar mais" acumulando as próximas. */
export function useMovieReviews(skMovieId: string): ReviewsResult {
  const [attempt, setAttempt] = useState(0)
  // Tudo guarda a chave da carga a que pertence; ao trocar de filme, o que é de
  // outra chave é ignorado, sem precisar limpar estado dentro do efeito.
  const requestKey = `${skMovieId}|${attempt}`
  const [loaded, setLoaded] = useState<LoadedReviews | null>(null)
  const [firstError, setFirstError] = useState<{ key: string; message: string } | null>(null)
  const [more, setMore] = useState<{ key: string; loading: boolean; error: string | null } | null>(
    null,
  )

  useEffect(() => {
    const controller = new AbortController()

    listMovieReviews(skMovieId, { page: 1 }, controller.signal)
      .then((data) =>
        setLoaded({ key: requestKey, items: data.items, total: data.total, page: 1, pages: data.pages }),
      )
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setFirstError({
          key: requestKey,
          message: errorMessage(error, 'Erro inesperado ao carregar as avaliações.'),
        })
      })

    return () => controller.abort()
  }, [skMovieId, requestKey])

  const current = loaded?.key === requestKey ? loaded : null
  const error = firstError?.key === requestKey ? firstError.message : null
  const moreState = more?.key === requestKey ? more : null

  function loadMore() {
    if (current === null || moreState?.loading) return
    setMore({ key: requestKey, loading: true, error: null })
    listMovieReviews(skMovieId, { page: current.page + 1 })
      .then((data) => {
        // Acrescenta a nova página às já exibidas (CA-19).
        setLoaded({
          ...current,
          items: [...current.items, ...data.items],
          total: data.total,
          page: current.page + 1,
          pages: data.pages,
        })
        setMore({ key: requestKey, loading: false, error: null })
      })
      .catch((loadError: unknown) => {
        // As avaliações já exibidas continuam na tela (CA-22).
        const message = errorMessage(loadError, 'Erro inesperado ao carregar mais avaliações.')
        setMore({ key: requestKey, loading: false, error: message })
      })
  }

  return {
    status: current ? 'success' : error ? 'error' : 'loading',
    message: error,
    items: current?.items ?? [],
    total: current?.total ?? 0,
    hasMore: current !== null && current.page < current.pages,
    loadingMore: moreState?.loading ?? false,
    loadMoreError: moreState?.error ?? null,
    retry: () => setAttempt((value) => value + 1),
    loadMore,
  }
}
