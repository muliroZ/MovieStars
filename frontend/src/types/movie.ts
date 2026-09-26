/** Espelha `MovieListItem` do backend (app/movies/schemas.py). */
export interface MovieListItem {
  sk_movie_id: string
  titulo: string
  ano_lancamento: number | null
  url_poster: string | null
  /** 0 a 5 estrelas, com 1 casa; null quando não há avaliações. */
  media_estrelas: number | null
  qtd_avaliacoes: number
  generos: string[]
  diretores: string[]
}

/** Resposta paginada padrão da API (constituição, seção 4.6). */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
