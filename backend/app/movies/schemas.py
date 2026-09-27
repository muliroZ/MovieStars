"""Schemas Pydantic de entrada e saída da API de filmes."""

from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, StringConstraints, ValidationInfo, field_validator

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


MovieStatus = Literal["Lançado", "Pós-Produção", "Em Produção", "Planejado"]
MIN_YEAR = 1888  # primeiro filme conhecido (spec 003, D-5)
MAX_YEARS_AHEAD = 10
URL_PREFIXES = ("http://", "https://")

# Textos obrigatórios: sem espaços nas pontas e não vazios (spec 003, D-10).
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
GenreName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
DirectorName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class MovieInput(BaseModel):
    """Dados do formulário de cadastro e edição de filme (POST e PUT).

    Gêneros e diretores vão pelo nome, que é único no banco (plan 003, DEC-3).
    """

    titulo: Title
    # data antes do ano: o validador do ano precisa enxergar a data (CA-8).
    data_lancamento: date | None = None
    ano_lancamento: int
    status_filme: MovieStatus
    duracao_minutos: int | None = Field(default=None, ge=1, le=1000)
    sinopse: str | None = Field(default=None, max_length=4000)
    url_poster: str | None = Field(default=None, max_length=2048)
    url_backdrop: str | None = Field(default=None, max_length=2048)
    generos: list[GenreName] = []
    diretores: list[DirectorName] = []

    @field_validator("sinopse", "url_poster", "url_backdrop", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        """Campo opcional vazio (ou só com espaços) significa "não informado"."""

        return None if isinstance(value, str) and value.strip() == "" else value

    @field_validator("url_poster", "url_backdrop")
    @classmethod
    def http_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(URL_PREFIXES):
            raise ValueError("Deve começar com http:// ou https://.")
        return value

    @field_validator("ano_lancamento")
    @classmethod
    def year_in_range_and_matches_date(cls, value: int, info: ValidationInfo) -> int:
        max_year = date.today().year + MAX_YEARS_AHEAD
        if not MIN_YEAR <= value <= max_year:
            raise ValueError(f"Deve estar entre {MIN_YEAR} e {max_year}.")
        release_date = info.data.get("data_lancamento")
        if release_date is not None and release_date.year != value:
            raise ValueError("O ano deve ser o mesmo da data de lançamento.")
        return value

    @field_validator("generos", "diretores")
    @classmethod
    def without_repeats(cls, values: list[str]) -> list[str]:
        """Remove repetidos mantendo a ordem (CA-18)."""

        return list(dict.fromkeys(values))


ReviewerName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
ReviewComment = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class ReviewInput(BaseModel):
    """Nova avaliação: nota em estrelas inteiras de 1 a 5 (constituição, seção 4.1)."""

    nome: ReviewerName
    estrelas: int = Field(ge=1, le=5)
    comentario: ReviewComment


GenreMode = Literal["any", "all"]
ReviewsFilter = Literal["all", "with", "without"]
SortField = Literal["title", "year", "rating", "reviews"]


class CatalogFilters(BaseModel):
    """Filtros e ordenação do catálogo (feature 100). Vazio/padrão = sem restrição."""

    genre: list[str] = Field(default=[], description="Nome do gênero; pode repetir.")
    genre_mode: GenreMode = Field(
        default="any", description="any: qualquer um dos gêneros; all: todos eles."
    )
    year_min: int | None = Field(default=None, description="Ano inicial (inclusivo).")
    year_max: int | None = Field(default=None, description="Ano final (inclusivo).")
    status: list[MovieStatus] = Field(default=[], description="Status; pode repetir.")
    reviews: ReviewsFilter = Field(
        default="all", description="all, with (com avaliação) ou without (sem avaliação)."
    )
    min_stars: int | None = Field(
        default=None, ge=1, le=5, description="Média exibida mínima, de 1 a 5 estrelas."
    )
    sort: SortField = Field(default="title", description="title, year, rating ou reviews.")
    reverse: bool = Field(default=False, description="Inverte a direção padrão do campo.")

    @field_validator("year_min")
    @classmethod
    def year_min_in_range(cls, value: int | None) -> int | None:
        return _check_year_range(value)

    @field_validator("year_max")
    @classmethod
    def year_max_in_range_and_after_min(cls, value: int | None, info: ValidationInfo) -> int | None:
        _check_year_range(value)
        year_min = info.data.get("year_min")
        if value is not None and year_min is not None and year_min > value:
            raise ValueError("O ano inicial deve ser menor ou igual ao final.")
        return value


def _check_year_range(value: int | None) -> int | None:
    """Mesma faixa de ano do cadastro de filmes (spec 003, D-5)."""

    max_year = date.today().year + MAX_YEARS_AHEAD
    if value is not None and not MIN_YEAR <= value <= max_year:
        raise ValueError(f"Deve estar entre {MIN_YEAR} e {max_year}.")
    return value


class CatalogQuery(CatalogFilters):
    """Parâmetros de GET /movies: paginação e busca (001) mais filtros e ordenação (100)."""

    page: int = Field(default=1, ge=1, description="Página, começando em 1.")
    page_size: int = Field(default=20, ge=1, le=100, description="Filmes por página (1 a 100).")
    search: str = Field(
        default="",
        max_length=200,
        description="Parte do título; não diferencia acentos nem maiúsculas.",
    )

    def filters(self) -> CatalogFilters:
        """Só os filtros e a ordenação, sem paginação e busca."""

        return CatalogFilters.model_validate(
            self.model_dump(exclude={"page", "page_size", "search"})
        )
