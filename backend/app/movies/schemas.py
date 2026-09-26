"""Schemas Pydantic de entrada e saída da API de filmes."""

from pydantic import BaseModel


class MovieListItem(BaseModel):
    """Um filme no catálogo, com o que o cartão precisa mostrar."""

    sk_movie_id: str
    titulo: str
    ano_lancamento: int | None
    url_poster: str | None
    media_estrelas: float | None  # 0 a 5, com 1 casa; None sem avaliações
    qtd_avaliacoes: int
    generos: list[str]
    diretores: list[str]


class MoviePage(BaseModel):
    """Página do catálogo no formato padrão da constituição (seção 4.6)."""

    items: list[MovieListItem]
    total: int
    page: int
    page_size: int
    pages: int
