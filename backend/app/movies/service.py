"""Consultas e regras de negócio do domínio de filmes."""

import math
from datetime import UTC
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import ColumnElement, Subquery, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import query_cache
from app.movies.models import (
    DimGenre,
    DimMovie,
    DimPerson,
    FactMoviePerformance,
    MovieReview,
    bridge_movie_genre,
)
from app.movies.normalization import normalize_title
from app.movies.schemas import (
    CatalogFilters,
    MovieDetail,
    MovieFinancials,
    MovieInput,
    MovieListItem,
    Page,
    ReviewInput,
    ReviewItem,
)


async def list_movies(
    db: AsyncSession,
    page: int,
    page_size: int,
    search: str = "",
    filters: CatalogFilters | None = None,
) -> Page[MovieListItem]:
    """Catálogo paginado, com busca pelo título, filtros e ordenação.

    `search` filtra por qualquer parte do título, sem diferenciar acentos e
    maiúsculas. Sem `filters`, a ordem é a alfabética da feature 001.
    """

    filters = filters or CatalogFilters()
    stats = _review_stats()
    conditions = _filter_conditions(filters, search, stats)

    count_query = select(func.count()).select_from(DimMovie)
    if _filters_need_stats(filters):
        count_query = count_query.outerjoin(stats, stats.c.sk_movie_id == DimMovie.sk_movie_id)
    total = await db.scalar(count_query.where(*conditions))

    offset = (page - 1) * page_size
    movies: list[DimMovie] = []
    # Página além da última: lista vazia sem consultar. Isso também evita estourar o
    # limite de 64 bits do OFFSET do SQLite com páginas enormes (ex.: page=10**18).
    if offset < total:
        # Etapa 1: só as chaves, na ordem. Ordenar sem carregar todas as colunas
        # (sinopses etc.) deixa as páginas fundas bem mais rápidas (plan 100, DEC-15).
        keys_query = select(DimMovie.sk_movie_id)
        if _needs_stats(filters):
            keys_query = keys_query.outerjoin(stats, stats.c.sk_movie_id == DimMovie.sk_movie_id)
        page_keys = list(
            await db.scalars(
                keys_query.where(*conditions)
                .order_by(*_order_by(filters, stats))
                .offset(offset)
                .limit(page_size)
            )
        )
        # Etapa 2: os filmes dessas chaves, com gêneros e pessoas em 2 consultas (sem N+1
        # e sem lazy load, que em código assíncrono gera MissingGreenlet).
        result = await db.scalars(
            select(DimMovie)
            .where(DimMovie.sk_movie_id.in_(page_keys))
            .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
        )
        movies_by_key = {movie.sk_movie_id: movie for movie in result}
        movies = [movies_by_key[key] for key in page_keys]  # mantém a ordem da etapa 1
    ratings = await _ratings_by_movie(db, [movie.sk_movie_id for movie in movies])

    return Page[MovieListItem](
        items=[_to_list_item(movie, ratings.get(movie.sk_movie_id)) for movie in movies],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


def _review_stats() -> Subquery:
    """Média (0–10) e quantidade de avaliações por filme, calculadas na consulta (4.2).

    O índice cobridor (sk_movie_id, nota) responde sem ler a tabela.
    """

    return (
        select(
            MovieReview.sk_movie_id,
            func.avg(MovieReview.nota).label("media"),
            func.count().label("qtd"),
        )
        .group_by(MovieReview.sk_movie_id)
        .subquery("review_stats")
    )


def _filters_need_stats(filters: CatalogFilters) -> bool:
    """Algum filtro usa a média ou a quantidade de avaliações."""

    return filters.reviews == "with" or filters.min_stars is not None


def _needs_stats(filters: CatalogFilters) -> bool:
    """O agregado só entra quando um filtro ou a ordenação precisa dele (plan 100, DEC-4)."""

    return _filters_need_stats(filters) or filters.sort in ("rating", "reviews")


def _filter_conditions(
    filters: CatalogFilters, search: str, stats: Subquery
) -> list[ColumnElement[bool]]:
    """Condições do WHERE: busca pelo título e filtros; cada filtro vazio não restringe."""

    conditions: list[ColumnElement[bool]] = []
    term = normalize_title(search.strip())
    if term:
        # autoescape: "%" e "_" do termo são texto comum, não curingas do LIKE.
        conditions.append(DimMovie.titulo_normalizado.contains(term, autoescape=True))

    genres = list(dict.fromkeys(filters.genre))
    if genres:
        movies_with_genres = (
            select(bridge_movie_genre.c.sk_movie_id)
            .join(DimGenre, DimGenre.sk_genre_id == bridge_movie_genre.c.sk_genre_id)
            .where(DimGenre.nome_genero.in_(genres))
        )
        if filters.genre_mode == "all":
            # Todos os gêneros: o filme precisa aparecer uma vez para cada um.
            movies_with_genres = movies_with_genres.group_by(
                bridge_movie_genre.c.sk_movie_id
            ).having(func.count() == len(genres))
        conditions.append(DimMovie.sk_movie_id.in_(movies_with_genres))

    if filters.year_min is not None:
        conditions.append(DimMovie.ano_lancamento >= filters.year_min)
    if filters.year_max is not None:
        conditions.append(DimMovie.ano_lancamento <= filters.year_max)
    if filters.status:
        conditions.append(DimMovie.status_filme.in_(filters.status))

    if filters.reviews == "with":
        conditions.append(stats.c.qtd.is_not(None))
    elif filters.reviews == "without":
        # NOT EXISTS usa o índice por filme, sem calcular médias (DEC-5).
        has_review = select(MovieReview.sk_movie_id).where(
            MovieReview.sk_movie_id == DimMovie.sk_movie_id
        )
        conditions.append(~has_review.exists())

    if filters.min_stars is not None:
        # Compara a média exibida (1 casa decimal), a mesma do cartão (DEC-6).
        conditions.append(func.round(stats.c.media / 2, 1) >= filters.min_stars)

    return conditions


def _order_by(filters: CatalogFilters, stats: Subquery) -> list[ColumnElement[Any]]:
    """Ordem do catálogo (spec 100, CA-13 a CA-16).

    Cada campo tem uma direção padrão, trocada por `reverse`. Valores vazios (sem ano,
    sem avaliação) ficam sempre no fim, e empates seguem o título, o ano e a chave,
    para a ordem ser estável entre páginas. A ordem por título A–Z usa o índice
    ix_dim_movies_ordem_catalogo.
    """

    tiebreak = [DimMovie.titulo_normalizado, DimMovie.ano_lancamento, DimMovie.sk_movie_id]
    reverse = filters.reverse

    if filters.sort == "title":
        if not reverse:
            return tiebreak
        return [DimMovie.titulo_normalizado.desc(), DimMovie.ano_lancamento, DimMovie.sk_movie_id]

    if filters.sort == "year":  # padrão: mais recentes primeiro
        year = DimMovie.ano_lancamento
        primary = (year.asc() if reverse else year.desc()).nulls_last()
    elif filters.sort == "rating":  # padrão: maiores médias primeiro
        average = stats.c.media
        primary = (average.asc() if reverse else average.desc()).nulls_last()
    else:  # "reviews" — padrão: mais avaliados primeiro; sem avaliação conta como 0
        count = func.coalesce(stats.c.qtd, 0)
        primary = count.asc() if reverse else count.desc()
    return [primary, *tiebreak]


async def _ratings_by_movie(db: AsyncSession, movie_ids: list[str]) -> dict[str, tuple[float, int]]:
    """Média (escala 0–10) e quantidade de avaliações de cada filme, via AVG no banco."""

    if not movie_ids:
        return {}
    rows = await db.execute(
        select(MovieReview.sk_movie_id, func.avg(MovieReview.nota), func.count())
        .where(MovieReview.sk_movie_id.in_(movie_ids))
        .group_by(MovieReview.sk_movie_id)
    )
    return {movie_id: (average, count) for movie_id, average, count in rows}


def _to_stars(nota: float | None) -> float | None:
    """Converte uma nota ou média do banco (0–10) em estrelas (0–5), com 1 casa.

    É o único lugar dessa conversão na leitura (constituição, seção 4.1).
    """

    return None if nota is None else round(nota / 2, 1)


def _to_nota(estrelas: int) -> float:
    """Converte estrelas (1–5) em nota do banco (0–10): a outra metade de `_to_stars`.

    As duas funções são as únicas conversões de escala (constituição, seção 4.1).
    """

    return float(estrelas * 2)


def _to_list_item(movie: DimMovie, rating: tuple[float, int] | None) -> MovieListItem:
    average, count = rating if rating else (None, 0)
    return MovieListItem(
        sk_movie_id=movie.sk_movie_id,
        titulo=movie.titulo,
        ano_lancamento=movie.ano_lancamento,
        url_poster=movie.url_poster,
        media_estrelas=_to_stars(average),
        qtd_avaliacoes=count,
        generos=sorted(genre.nome_genero for genre in movie.genres),
        diretores=_names_by_type(movie.people)["Diretor"],
    )


async def get_movie(db: AsyncSession, sk_movie_id: str) -> MovieDetail | None:
    """Detalhes de um filme, com equipe, produtoras, métricas e média; None se não existe."""

    movie = await db.scalar(
        select(DimMovie)
        .where(DimMovie.sk_movie_id == sk_movie_id)
        .options(
            selectinload(DimMovie.genres),
            selectinload(DimMovie.people),
            selectinload(DimMovie.companies),
            selectinload(DimMovie.performance),
        )
    )
    if movie is None:
        return None

    ratings = await _ratings_by_movie(db, [movie.sk_movie_id])
    average, count = ratings.get(movie.sk_movie_id, (None, 0))
    people = _names_by_type(movie.people)
    return MovieDetail(
        sk_movie_id=movie.sk_movie_id,
        titulo=movie.titulo,
        ano_lancamento=movie.ano_lancamento,
        data_lancamento=movie.data_lancamento,
        duracao_minutos=movie.duracao_minutos,
        status_filme=movie.status_filme,
        sinopse=movie.sinopse,
        url_poster=movie.url_poster,
        url_backdrop=movie.url_backdrop,
        generos=sorted(genre.nome_genero for genre in movie.genres),
        diretores=people["Diretor"],
        roteiristas=people["Roteirista"],
        elenco=people["Ator"],
        produtoras=sorted(company.nome_produtora for company in movie.companies),
        financeiro=_to_financials(movie.performance),
        media_estrelas=_to_stars(average),
        qtd_avaliacoes=count,
    )


def _names_by_type(people: list[DimPerson]) -> dict[str, list[str]]:
    """Nomes separados por tipo de pessoa (Diretor, Roteirista, Ator), em ordem alfabética."""

    names: dict[str, list[str]] = {"Diretor": [], "Roteirista": [], "Ator": []}
    for person in people:
        names[person.tipo_pessoa].append(person.nome_pessoa)
    return {tipo: sorted(values) for tipo, values in names.items()}


def _to_financials(performance: FactMoviePerformance | None) -> MovieFinancials | None:
    if performance is None:
        return None

    def money(value: Decimal | None) -> float | None:
        return None if value is None else float(value)

    def profit(budget: Decimal | None, revenue: Decimal | None, lucro: Decimal) -> float | None:
        # Sem orçamento ou receita, o lucro gravado (−orçamento ou 0) não tem significado.
        return money(lucro) if budget is not None and revenue is not None else None

    return MovieFinancials(
        orcamento_brl=money(performance.orcamento_brl),
        receita_brl=money(performance.receita_brl),
        lucro_brl=profit(performance.orcamento_brl, performance.receita_brl, performance.lucro_brl),
        orcamento_usd=money(performance.orcamento_usd),
        receita_usd=money(performance.receita_usd),
        lucro_usd=profit(performance.orcamento_usd, performance.receita_usd, performance.lucro_usd),
    )


async def list_reviews(
    db: AsyncSession, sk_movie_id: str, page: int, page_size: int
) -> Page[ReviewItem] | None:
    """Avaliações de um filme, das mais recentes para as mais antigas.

    Devolve None se o filme não existe (a rota responde 404).
    """

    movie_exists = await db.scalar(
        select(DimMovie.sk_movie_id).where(DimMovie.sk_movie_id == sk_movie_id)
    )
    if movie_exists is None:
        return None

    total = await db.scalar(
        select(func.count()).select_from(MovieReview).where(MovieReview.sk_movie_id == sk_movie_id)
    )
    offset = (page - 1) * page_size
    reviews: list[MovieReview] = []
    if offset < total:  # página além da última: lista vazia sem consultar
        result = await db.scalars(
            select(MovieReview)
            .where(MovieReview.sk_movie_id == sk_movie_id)
            # Desempate pela chave: as avaliações importadas têm todas a mesma data.
            .order_by(MovieReview.created_at.desc(), MovieReview.sk_movie_review_id)
            .offset(offset)
            .limit(page_size)
        )
        reviews = list(result.all())

    return Page[ReviewItem](
        items=[_to_review_item(review) for review in reviews],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


def _to_review_item(review: MovieReview) -> ReviewItem:
    return ReviewItem(
        sk_movie_review_id=review.sk_movie_review_id,
        nome=review.nome,
        estrelas=_to_stars(review.nota),
        comentario=review.comentario,
        # O SQLite grava CURRENT_TIMESTAMP em UTC, sem fuso: deixamos o fuso explícito
        # para a interface converter para o horário local.
        created_at=review.created_at.replace(tzinfo=UTC),
    )


DIRECTOR_SUGGESTIONS = 10


async def list_genres(db: AsyncSession) -> list[str]:
    """Nomes dos gêneros cadastrados, em ordem alfabética."""

    return list(await db.scalars(select(DimGenre.nome_genero).order_by(DimGenre.nome_genero)))


async def search_directors(db: AsyncSession, search: str) -> list[str]:
    """Até 10 diretores cujo nome contém o termo, sem diferenciar acentos e maiúsculas.

    Ordem: o nome exatamente igual ao digitado, depois os que começam com o termo,
    depois os demais em ordem alfabética.
    """

    typed = search.strip()
    term = normalize_title(typed)
    starts_with_term = DimPerson.nome_normalizado.startswith(term, autoescape=True)
    names = await db.scalars(
        select(DimPerson.nome_pessoa)
        .where(
            DimPerson.tipo_pessoa == "Diretor",
            DimPerson.nome_normalizado.contains(term, autoescape=True),
        )
        .order_by(
            (DimPerson.nome_pessoa == typed).desc(),
            starts_with_term.desc(),
            DimPerson.nome_normalizado,
            DimPerson.nome_pessoa,
        )
        .limit(DIRECTOR_SUGGESTIONS)
    )
    return list(names)


class UnknownGenresError(Exception):
    """Um ou mais gêneros do formulário não existem (gêneros não são criados, CA-13)."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        label = "Gênero inexistente" if len(names) == 1 else "Gêneros inexistentes"
        super().__init__(f"{label}: {', '.join(names)}.")


async def create_movie(db: AsyncSession, data: MovieInput) -> MovieDetail:
    """Cadastra um filme; o id_filme é gerado aqui (constituição, seção 4.4)."""

    genres = await _genres_by_name(db, data.generos)
    directors = await _directors_by_name(db, data.diretores)
    movie = DimMovie(
        id_filme=str(uuid4()),
        genres=genres,
        people=directors,
        **_editable_fields(data),
    )
    db.add(movie)
    await db.commit()
    query_cache.clear()  # um filme novo muda totais e paginação (plan 101, DEC-3)

    detail = await get_movie(db, movie.sk_movie_id)
    assert detail is not None  # acabou de ser criado
    return detail


async def update_movie(db: AsyncSession, sk_movie_id: str, data: MovieInput) -> MovieDetail | None:
    """Atualiza os campos editáveis de um filme; None se ele não existe."""

    movie = await db.scalar(
        select(DimMovie)
        .where(DimMovie.sk_movie_id == sk_movie_id)
        .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
    )
    if movie is None:
        return None

    genres = await _genres_by_name(db, data.generos)
    directors = await _directors_by_name(db, data.diretores)
    for column, value in _editable_fields(data).items():
        setattr(movie, column, value)
    # O default de titulo_normalizado só roda no insert (plan 003, DEC-7).
    movie.titulo_normalizado = normalize_title(data.titulo)
    movie.genres = genres
    # `people` também guarda roteiristas e atores, que o formulário não edita (CA-22).
    movie.people = [
        person for person in movie.people if person.tipo_pessoa != "Diretor"
    ] + directors
    await db.commit()
    query_cache.clear()
    return await get_movie(db, sk_movie_id)


async def delete_movie(db: AsyncSession, sk_movie_id: str) -> bool:
    """Remove o filme definitivamente; False se ele não existia (constituição, seção 4.5).

    As chaves estrangeiras com ON DELETE CASCADE apagam avaliações, vínculos, métricas
    e o resumo de avaliações (o PRAGMA foreign_keys é ligado em db/session.py).
    Pessoas, gêneros e produtoras continuam cadastrados.
    """

    result = await db.execute(delete(DimMovie).where(DimMovie.sk_movie_id == sk_movie_id))
    await db.commit()
    deleted = result.rowcount > 0
    if deleted:  # remover um filme inexistente não muda nada (spec 101, CA-11)
        query_cache.clear()
    return deleted


def _editable_fields(data: MovieInput) -> dict[str, Any]:
    """Colunas de `dim_movies` que o formulário edita."""

    return {
        "titulo": data.titulo,
        "data_lancamento": data.data_lancamento,
        "ano_lancamento": data.ano_lancamento,
        "status_filme": data.status_filme,
        "duracao_minutos": data.duracao_minutos,
        "sinopse": data.sinopse,
        "url_poster": data.url_poster,
        "url_backdrop": data.url_backdrop,
    }


async def _genres_by_name(db: AsyncSession, names: list[str]) -> list[DimGenre]:
    """Gêneros pelo nome, na ordem pedida; UnknownGenresError se algum não existir."""

    if not names:
        return []
    found = {
        genre.nome_genero: genre
        for genre in await db.scalars(select(DimGenre).where(DimGenre.nome_genero.in_(names)))
    }
    missing = [name for name in names if name not in found]
    if missing:
        raise UnknownGenresError(missing)
    return [found[name] for name in names]


async def _directors_by_name(db: AsyncSession, names: list[str]) -> list[DimPerson]:
    """Diretores pelo nome exato: reaproveita os existentes e cria os demais (spec 003, D-3).

    O par (nome, tipo) é único no banco, então o nome exato acha no máximo um diretor.
    """

    if not names:
        return []
    existing = {
        person.nome_pessoa: person
        for person in await db.scalars(
            select(DimPerson).where(
                DimPerson.tipo_pessoa == "Diretor", DimPerson.nome_pessoa.in_(names)
            )
        )
    }
    return [
        existing.get(name) or DimPerson(nome_pessoa=name, tipo_pessoa="Diretor") for name in names
    ]


async def create_review(db: AsyncSession, sk_movie_id: str, data: ReviewInput) -> ReviewItem | None:
    """Grava uma avaliação nova; None se o filme não existe (a rota responde 404).

    O resumo `dim_reviews` não é atualizado: a média vem sempre do AVG das
    avaliações individuais (constituição, seção 4.2).
    """

    movie_exists = await db.scalar(
        select(DimMovie.sk_movie_id).where(DimMovie.sk_movie_id == sk_movie_id)
    )
    if movie_exists is None:
        return None

    review = MovieReview(
        sk_movie_id=sk_movie_id,
        nome=data.nome,
        nota=_to_nota(data.estrelas),
        comentario=data.comentario,
    )
    db.add(review)
    await db.commit()
    query_cache.clear()  # a média e a quantidade mudam em qualquer página
    await db.refresh(review)  # lê o created_at preenchido pelo banco
    return _to_review_item(review)
