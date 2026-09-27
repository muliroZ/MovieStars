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

/** Espelha `MovieFinancials`: valores em real e dólar; lucro null quando não calculável. */
export interface MovieFinancials {
  orcamento_brl: number | null
  receita_brl: number | null
  lucro_brl: number | null
  orcamento_usd: number | null
  receita_usd: number | null
  lucro_usd: number | null
}

/** Espelha `MovieDetail` do backend. */
export interface MovieDetail {
  sk_movie_id: string
  titulo: string
  ano_lancamento: number | null
  /** "AAAA-MM-DD" */
  data_lancamento: string | null
  duracao_minutos: number | null
  status_filme: string | null
  sinopse: string | null
  url_poster: string | null
  url_backdrop: string | null
  generos: string[]
  diretores: string[]
  roteiristas: string[]
  elenco: string[]
  produtoras: string[]
  financeiro: MovieFinancials | null
  media_estrelas: number | null
  qtd_avaliacoes: number
}

/** Espelha `ReviewItem` do backend. */
export interface Review {
  sk_movie_review_id: string
  nome: string
  /** 0 a 5, com 1 casa. */
  estrelas: number
  comentario: string
  /** Data e hora em UTC ("…Z"). */
  created_at: string
}
