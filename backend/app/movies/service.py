"""Consultas e regras de negócio do domínio de filmes."""

import math
from datetime import UTC
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import DimGenre, DimMovie, DimPerson, FactMoviePerformance, MovieReview
from app.movies.normalization import normalize_title
from app.movies.schemas import (
    MovieDetail,
    MovieFinancials,
    MovieInput,
    MovieListItem,
    Page,
    ReviewItem,
)


async def list_movies(
    db: AsyncSession, page: int, page_size: int, search: str = ""
) -> Page[MovieListItem]:
    """Catálogo paginado, em ordem alfabética sem diferenciar acentos e maiúsculas.

    `search` filtra por qualquer parte do título, também sem diferenciar acentos e
    maiúsculas; vazio (ou só espaços) mostra o catálogo completo.
    """

    filters = []
    term = normalize_title(search.strip())
    if term:
        # autoescape: "%" e "_" do termo são texto comum, não curingas do LIKE.
        filters.append(DimMovie.titulo_normalizado.contains(term, autoescape=True))

    total = await db.scalar(select(func.count()).select_from(DimMovie).where(*filters))
    offset = (page - 1) * page_size
    movies: list[DimMovie] = []
    # Página além da última: lista vazia sem consultar. Isso também evita estourar o
    # limite de 64 bits do OFFSET do SQLite com páginas enormes (ex.: page=10**18).
    if offset < total:
        result = await db.scalars(
            select(DimMovie)
            .where(*filters)
            # O índice ix_dim_movies_ordem_catalogo cobre exatamente esta ordem.
            .order_by(DimMovie.titulo_normalizado, DimMovie.ano_lancamento, DimMovie.sk_movie_id)
            .offset(offset)
            .limit(page_size)
            # Carrega gêneros e pessoas dos filmes da página em 2 consultas (sem N+1 e
            # sem lazy load, que em código assíncrono gera MissingGreenlet).
            .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
        )
        movies = list(result.all())
    ratings = await _ratings_by_movie(db, [movie.sk_movie_id for movie in movies])

    return Page[MovieListItem](
        items=[_to_list_item(movie, ratings.get(movie.sk_movie_id)) for movie in movies],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


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
    return await get_movie(db, sk_movie_id)


async def delete_movie(db: AsyncSession, sk_movie_id: str) -> bool:
    """Remove o filme definitivamente; False se ele não existia (constituição, seção 4.5).

    As chaves estrangeiras com ON DELETE CASCADE apagam avaliações, vínculos, métricas
    e o resumo de avaliações (o PRAGMA foreign_keys é ligado em db/session.py).
    Pessoas, gêneros e produtoras continuam cadastrados.
    """

    result = await db.execute(delete(DimMovie).where(DimMovie.sk_movie_id == sk_movie_id))
    await db.commit()
    return result.rowcount > 0


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
