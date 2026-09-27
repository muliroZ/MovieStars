import type {
  MovieDetail,
  MovieInput,
  MovieListItem,
  Page,
  Review,
  ReviewInput,
} from '../types/movie'
import { apiGet, apiSend } from './client'

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

/** POST /movies: cadastra um filme e devolve os detalhes dele. */
export function createMovie(input: MovieInput): Promise<MovieDetail> {
  return apiSend<MovieDetail>('POST', '/movies', input)
}

/** PUT /movies/{id}: atualiza os campos editáveis e devolve os detalhes. */
export function updateMovie(skMovieId: string, input: MovieInput): Promise<MovieDetail> {
  return apiSend<MovieDetail>('PUT', `/movies/${encodeURIComponent(skMovieId)}`, input)
}

/** DELETE /movies/{id}: remove o filme definitivamente. */
export function deleteMovie(skMovieId: string): Promise<void> {
  return apiSend<void>('DELETE', `/movies/${encodeURIComponent(skMovieId)}`)
}

/** GET /genres: nomes dos gêneros em ordem alfabética. */
export function listGenres(signal?: AbortSignal): Promise<string[]> {
  return apiGet<string[]>('/genres', {}, signal)
}

/** GET /directors: até 10 sugestões de diretores pelo nome. */
export function searchDirectors(search: string, signal?: AbortSignal): Promise<string[]> {
  return apiGet<string[]>('/directors', { search }, signal)
}

/** POST /movies/{id}/reviews: grava uma avaliação e devolve como ela ficou. */
export function createReview(skMovieId: string, input: ReviewInput): Promise<Review> {
  return apiSend<Review>('POST', `/movies/${encodeURIComponent(skMovieId)}/reviews`, input)
}
