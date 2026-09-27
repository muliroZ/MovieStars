/**
 * Formulário de filme (cadastro e edição): valores, validação e conversão para a API.
 *
 * As regras e mensagens repetem as do backend (`MovieInput`), para avisar antes de
 * enviar (spec 003, CA-14). Os nomes dos campos são os mesmos da API, então os erros
 * que o servidor devolver caem direto no campo certo.
 */

import type { MovieDetail, MovieInput, MovieStatus } from '../types/movie'

export const MOVIE_STATUSES: MovieStatus[] = ['Lançado', 'Pós-Produção', 'Em Produção', 'Planejado']
export const MIN_YEAR = 1888
const MAX_YEARS_AHEAD = 10
const URL_PREFIXES = ['http://', 'https://']

/** Valores como ficam nos campos (texto), antes da conversão para a API. */
export interface MovieFormValues {
  titulo: string
  data_lancamento: string // "AAAA-MM-DD" do campo de data, ou ""
  ano_lancamento: string
  status_filme: MovieStatus | ''
  duracao_minutos: string
  sinopse: string
  url_poster: string
  url_backdrop: string
  generos: string[]
  diretores: string[]
}

export type MovieFormField = keyof MovieFormValues
export type MovieFormErrors = Partial<Record<MovieFormField, string>>

export const EMPTY_MOVIE_FORM: MovieFormValues = {
  titulo: '',
  data_lancamento: '',
  ano_lancamento: '',
  status_filme: '',
  duracao_minutos: '',
  sinopse: '',
  url_poster: '',
  url_backdrop: '',
  generos: [],
  diretores: [],
}

export function maxYear(): number {
  return new Date().getFullYear() + MAX_YEARS_AHEAD
}

/** Ano de uma data "AAAA-MM-DD" (para preencher o campo Ano ao escolher a data). */
export function yearOf(isoDate: string): string {
  return isoDate.slice(0, 4)
}

/** Preenche o formulário de edição com os dados atuais do filme. */
export function formFromMovie(movie: MovieDetail): MovieFormValues {
  return {
    titulo: movie.titulo,
    data_lancamento: movie.data_lancamento ?? '',
    ano_lancamento: movie.ano_lancamento === null ? '' : String(movie.ano_lancamento),
    status_filme: MOVIE_STATUSES.find((status) => status === movie.status_filme) ?? '',
    // Duração 0 da carga significa "não informada" (spec 000, D-2): campo vazio.
    duracao_minutos: movie.duracao_minutos ? String(movie.duracao_minutos) : '',
    sinopse: movie.sinopse ?? '',
    url_poster: movie.url_poster ?? '',
    url_backdrop: movie.url_backdrop ?? '',
    generos: movie.generos,
    diretores: movie.diretores,
  }
}

/** Converte valores já validados no corpo do POST/PUT. */
export function movieInputFromForm(values: MovieFormValues): MovieInput {
  const optional = (text: string) => (text.trim() === '' ? null : text)
  return {
    titulo: values.titulo.trim(),
    data_lancamento: values.data_lancamento || null,
    ano_lancamento: Number(values.ano_lancamento),
    status_filme: values.status_filme as MovieStatus, // validado antes
    duracao_minutos: values.duracao_minutos.trim() === '' ? null : Number(values.duracao_minutos),
    sinopse: optional(values.sinopse),
    url_poster: optional(values.url_poster.trim()),
    url_backdrop: optional(values.url_backdrop.trim()),
    generos: values.generos,
    diretores: values.diretores.map((name) => name.trim()),
  }
}

/** Erros por campo, com as mesmas regras e mensagens da API (spec 003, CA-6 a CA-12, CA-19). */
export function validateMovieForm(values: MovieFormValues): MovieFormErrors {
  const errors: MovieFormErrors = {}

  const title = values.titulo.trim()
  if (title === '') errors.titulo = 'Campo obrigatório.'
  else if (title.length > 500) errors.titulo = 'Deve ter no máximo 500 caracteres.'

  const dateError = validateDate(values.data_lancamento)
  if (dateError) errors.data_lancamento = dateError

  const yearError = validateYear(values.ano_lancamento, dateError ? '' : values.data_lancamento)
  if (yearError) errors.ano_lancamento = yearError

  if (values.status_filme === '') errors.status_filme = 'Campo obrigatório.'

  const duration = values.duracao_minutos.trim()
  if (duration !== '') {
    if (!/^\d+$/.test(duration)) errors.duracao_minutos = 'Deve ser um número inteiro.'
    else if (Number(duration) < 1) errors.duracao_minutos = 'Deve ser no mínimo 1.'
    else if (Number(duration) > 1000) errors.duracao_minutos = 'Deve ser no máximo 1000.'
  }

  if (values.sinopse.length > 4000) errors.sinopse = 'Deve ter no máximo 4000 caracteres.'

  for (const field of ['url_poster', 'url_backdrop'] as const) {
    const urlError = validateUrl(values[field])
    if (urlError) errors[field] = urlError
  }

  if (values.diretores.some((name) => name.trim().length > 255)) {
    errors.diretores = 'Deve ter no máximo 255 caracteres.'
  }

  return errors
}

function validateDate(value: string): string | null {
  if (value === '') return null
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return 'Data inválida.'
  const [year, month, day] = match.slice(1).map(Number)
  const date = new Date(year, month - 1, day)
  const exists = date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
  return exists ? null : 'Data inválida.' // ex.: 30/02
}

function validateYear(value: string, releaseDate: string): string | null {
  const year = value.trim()
  if (year === '') return 'Campo obrigatório.'
  if (!/^\d+$/.test(year)) return 'Deve ser um número inteiro.'
  if (Number(year) < MIN_YEAR || Number(year) > maxYear()) {
    return `Deve estar entre ${MIN_YEAR} e ${maxYear()}.`
  }
  if (releaseDate !== '' && yearOf(releaseDate) !== year) {
    return 'O ano deve ser o mesmo da data de lançamento.'
  }
  return null
}

function validateUrl(value: string): string | null {
  const url = value.trim()
  if (url === '') return null
  if (url.length > 2048) return 'Deve ter no máximo 2048 caracteres.'
  if (!URL_PREFIXES.some((prefix) => url.startsWith(prefix))) {
    return 'Deve começar com http:// ou https://.'
  }
  return null
}
