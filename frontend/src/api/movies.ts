import type { MovieListItem, Page } from '../types/movie'
import { apiGet } from './client'

export interface ListMoviesParams {
  page: number
  pageSize?: number
  search?: string
}

/** GET /movies: uma página do catálogo, com busca opcional pelo título. */
export function listMovies(
  { page, pageSize = 20, search = '' }: ListMoviesParams,
  signal?: AbortSignal,
): Promise<Page<MovieListItem>> {
  return apiGet<Page<MovieListItem>>('/movies', { page, page_size: pageSize, search }, signal)
}
