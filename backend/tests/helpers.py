"""Funções de apoio para montar dados de teste pelo ORM."""

from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import (
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    FactMoviePerformance,
    MovieReview,
)


async def add_movie(
    session: AsyncSession,
    titulo: str,
    ano: int | None = 2000,
    *,
    genres: list[DimGenre] | None = None,
    people: list[DimPerson] | None = None,
    companies: list[DimCompany] | None = None,
    notas: list[float] | None = None,
    reviews: list[MovieReview] | None = None,
    performance: FactMoviePerformance | None = None,
    **fields: Any,
) -> DimMovie:
    """Insere um filme pelo ORM (a chave e o id_filme são gerados).

    `notas` cria avaliações simples (todas com a mesma data); `reviews` aceita
    avaliações já montadas, por exemplo com `created_at` definido. `fields`
    repassa outras colunas de `DimMovie` (sinopse, duracao_minutos etc.).
    """

    movie = DimMovie(
        id_filme=uuid4().hex,
        titulo=titulo,
        ano_lancamento=ano,
        genres=genres or [],
        people=people or [],
        companies=companies or [],
        reviews=[
            *(reviews or []),
            *(MovieReview(nome="Ana", nota=nota, comentario="Comentário.") for nota in notas or []),
        ],
        performance=performance,
        **fields,
    )
    session.add(movie)
    await session.commit()
    return movie
