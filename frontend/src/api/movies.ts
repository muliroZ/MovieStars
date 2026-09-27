import type { MovieDetail, MovieListItem, Page, Review } from '../types/movie'
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

/** GET /movies/{id}: detalhes de um filme. Filme inexistente → ApiError com status 404. */
export function getMovie(skMovieId: string, signal?: AbortSignal): Promise<MovieDetail> {
  return apiGet<MovieDetail>(`/movies/${encodeURIComponent(skMovieId)}`, {}, signal)
}

export interface ListReviewsParams {
  page: number
  pageSize?: number
}

/** GET /movies/{id}/reviews: avaliações das mais recentes para as mais antigas. */
export function listMovieReviews(
  skMovieId: string,
  { page, pageSize = 10 }: ListReviewsParams,
  signal?: AbortSignal,
): Promise<Page<Review>> {
  return apiGet<Page<Review>>(
    `/movies/${encodeURIComponent(skMovieId)}/reviews`,
    { page, page_size: pageSize },
    signal,
  )
}
