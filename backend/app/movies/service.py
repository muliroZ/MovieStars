"""Consultas e regras de negócio do domínio de filmes."""

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.movies.models import DimMovie, MovieReview
from app.movies.normalization import normalize_title
from app.movies.schemas import MovieListItem, MoviePage


async def list_movies(db: AsyncSession, page: int, page_size: int, search: str = "") -> MoviePage:
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
    movies = await db.scalars(
        select(DimMovie)
        .where(*filters)
        # O índice ix_dim_movies_ordem_catalogo cobre exatamente esta ordem.
        .order_by(DimMovie.titulo_normalizado, DimMovie.ano_lancamento, DimMovie.sk_movie_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        # Carrega gêneros e pessoas dos filmes da página em 2 consultas (sem N+1 e
        # sem lazy load, que em código assíncrono gera MissingGreenlet).
        .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
    )
    movies = movies.all()
    ratings = await _ratings_by_movie(db, [movie.sk_movie_id for movie in movies])

    return MoviePage(
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


def _to_stars(average: float | None) -> float | None:
    """Converte a nota do banco (0–10) em estrelas (0–5), com 1 casa decimal.

    É o único lugar dessa conversão na leitura (constituição, seção 4.1).
    """

    return None if average is None else round(average / 2, 1)


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
        diretores=sorted(
            person.nome_pessoa for person in movie.people if person.tipo_pessoa == "Diretor"
        ),
    )
