/**
 * Filtros e ordenação do catálogo (feature 100): tipos, leitura e gravação na URL,
 * contagem de filtros ativos e conversão para os parâmetros da API.
 *
 * Os nomes na URL são os mesmos da API (plan 100, DEC-1). Valores padrão não vão
 * para a URL, e valores inválidos vindos dela são ignorados (spec 100, CA-20).
 */

import type { QueryParams } from '../api/client'
import type { MovieStatus } from '../types/movie'
import { MIN_YEAR, MOVIE_STATUSES, maxYear } from './movieForm'

export type GenreMode = 'any' | 'all'
export type ReviewsFilter = 'all' | 'with' | 'without'
export type SortField = 'title' | 'year' | 'rating' | 'reviews'

export interface CatalogFilters {
  genres: string[]
  genreMode: GenreMode
  yearMin: number | null
  yearMax: number | null
  status: MovieStatus[]
  reviews: ReviewsFilter
  minStars: number | null
  sort: SortField
  reverse: boolean
}

export const DEFAULT_FILTERS: CatalogFilters = {
  genres: [],
  genreMode: 'any',
  yearMin: null,
  yearMax: null,
  status: [],
  reviews: 'all',
  minStars: null,
  sort: 'title',
  reverse: false,
}

/** Rótulos da ordenação (spec 100, D-11). */
export const SORT_OPTIONS: { value: SortField; label: string }[] = [
  { value: 'title', label: 'Título' },
  { value: 'year', label: 'Ano' },
  { value: 'rating', label: 'Média de estrelas' },
  { value: 'reviews', label: 'Quantidade de avaliações' },
]

const GENRE_MODES: GenreMode[] = ['any', 'all']
const REVIEWS_OPTIONS: ReviewsFilter[] = ['all', 'with', 'without']
const SORT_FIELDS: SortField[] = SORT_OPTIONS.map((option) => option.value)

/** Chaves dos filtros na URL (as mesmas da API). */
const FILTER_KEYS = [
  'genre',
  'genre_mode',
  'year_min',
  'year_max',
  'status',
  'reviews',
  'min_stars',
  'sort',
  'reverse',
]

function isOneOf<T extends string>(options: readonly T[], value: string | null): value is T {
  return value !== null && (options as readonly string[]).includes(value)
}

/** Ano válido (inteiro na faixa do cadastro) ou null. */
function parseYear(raw: string | null): number | null {
  if (raw === null || !/^\d+$/.test(raw)) return null
  const year = Number(raw)
  return year >= MIN_YEAR && year <= maxYear() ? year : null
}

/** Lê os filtros da URL, ignorando valores inválidos. */
export function parseFilters(params: URLSearchParams): CatalogFilters {
  let yearMin = parseYear(params.get('year_min'))
  let yearMax = parseYear(params.get('year_max'))
  if (yearMin !== null && yearMax !== null && yearMin > yearMax) {
    // Faixa invertida é inválida como um todo: nenhum dos dois é aplicado.
    yearMin = null
    yearMax = null
  }
  const minStars = params.get('min_stars')

  return {
    genres: [...new Set(params.getAll('genre').filter((genre) => genre !== ''))],
    genreMode: isOneOf(GENRE_MODES, params.get('genre_mode')) ? (params.get('genre_mode') as GenreMode) : 'any',
    yearMin,
    yearMax,
    status: [...new Set(params.getAll('status').filter((status) => isOneOf(MOVIE_STATUSES, status)))] as MovieStatus[],
    reviews: isOneOf(REVIEWS_OPTIONS, params.get('reviews')) ? (params.get('reviews') as ReviewsFilter) : 'all',
    minStars: minStars !== null && /^[1-5]$/.test(minStars) ? Number(minStars) : null,
    sort: isOneOf(SORT_FIELDS, params.get('sort')) ? (params.get('sort') as SortField) : 'title',
    reverse: params.get('reverse') === 'true',
  }
}

/** Parâmetros não padrão dos filtros (valem para a URL e para a API). */
export function filtersToApiParams(filters: CatalogFilters): QueryParams {
  const params: QueryParams = {}
  if (filters.genres.length > 0) {
    params.genre = filters.genres
    if (filters.genreMode !== 'any') params.genre_mode = filters.genreMode
  }
  if (filters.yearMin !== null) params.year_min = filters.yearMin
  if (filters.yearMax !== null) params.year_max = filters.yearMax
  if (filters.status.length > 0) params.status = filters.status
  if (filters.reviews !== 'all') params.reviews = filters.reviews
  if (filters.minStars !== null) params.min_stars = filters.minStars
  if (filters.sort !== 'title') params.sort = filters.sort
  if (filters.reverse) params.reverse = true
  return params
}

/** Grava os filtros na URL, trocando os que já estavam e omitindo os padrões (CA-19). */
export function writeFilters(params: URLSearchParams, filters: CatalogFilters): void {
  for (const key of FILTER_KEYS) params.delete(key)
  for (const [key, value] of Object.entries(filtersToApiParams(filters))) {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item))
    else if (value !== undefined) params.set(key, String(value))
  }
}

/** Quantos tipos de filtro estão ativos ("Filtros (N)"); a ordenação não conta (CA-1, CA-17). */
export function activeFilterCount(filters: CatalogFilters): number {
  return [
    filters.genres.length > 0,
    filters.yearMin !== null || filters.yearMax !== null,
    filters.status.length > 0,
    filters.reviews !== 'all',
    filters.minStars !== null,
  ].filter(Boolean).length
}

/** Filtros zerados, mantendo a ordenação ("Limpar filtros", CA-12). */
export function clearFilters(filters: CatalogFilters): CatalogFilters {
  return { ...DEFAULT_FILTERS, sort: filters.sort, reverse: filters.reverse }
}

export interface YearRangeErrors {
  yearMin?: string
  yearMax?: string
}

/** Erros dos campos de ano, com as mesmas mensagens da API (CA-5). */
export function validateYearRange(yearMin: string, yearMax: string): YearRangeErrors {
  const errors: YearRangeErrors = {}
  const minError = validateYear(yearMin)
  const maxError = validateYear(yearMax)
  if (minError) errors.yearMin = minError
  if (maxError) errors.yearMax = maxError
  if (!minError && !maxError && yearMin.trim() !== '' && yearMax.trim() !== '') {
    if (Number(yearMin) > Number(yearMax)) {
      errors.yearMax = 'O ano inicial deve ser menor ou igual ao final.'
    }
  }
  return errors
}

function validateYear(value: string): string | null {
  const year = value.trim()
  if (year === '') return null
  if (!/^\d+$/.test(year)) return 'Deve ser um número inteiro.'
  if (Number(year) < MIN_YEAR || Number(year) > maxYear()) {
    return `Deve estar entre ${MIN_YEAR} e ${maxYear()}.`
  }
  return null
}
