"""Schemas Pydantic de entrada e saída da API de filmes."""

from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Resposta paginada no formato padrão da constituição (seção 4.6)."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


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


class MovieFinancials(BaseModel):
    """Métricas financeiras em real e em dólar, como estão no banco.

    `lucro_*` é None quando falta orçamento ou receita naquela moeda (spec 002, D-5).
    """

    orcamento_brl: float | None
    receita_brl: float | None
    lucro_brl: float | None
    orcamento_usd: float | None
    receita_usd: float | None
    lucro_usd: float | None


class MovieDetail(BaseModel):
    """Tudo o que a página de detalhes mostra sobre um filme."""

    sk_movie_id: str
    titulo: str
    ano_lancamento: int | None
    data_lancamento: date | None
    duracao_minutos: int | None
    status_filme: str | None
    sinopse: str | None
    url_poster: str | None
    url_backdrop: str | None
    generos: list[str]
    diretores: list[str]
    roteiristas: list[str]
    elenco: list[str]
    produtoras: list[str]
    financeiro: MovieFinancials | None  # None se o filme não tem métricas
    media_estrelas: float | None
    qtd_avaliacoes: int


class ReviewItem(BaseModel):
    """Uma avaliação individual, com a nota já convertida para estrelas."""

    sk_movie_review_id: str
    nome: str
    estrelas: float  # 0 a 5, com 1 casa (nota do banco ÷ 2)
    comentario: str
    created_at: datetime  # em UTC, serializado com "Z"
