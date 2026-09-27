"""Rotas HTTP do domínio de filmes."""

import json
from collections.abc import Awaitable, Callable
from typing import Annotated, TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import MISSING, query_cache
from app.db.session import get_db
from app.movies.schemas import (
    CatalogQuery,
    MovieDetail,
    MovieInput,
    MovieListItem,
    Page,
    ReviewInput,
    ReviewItem,
)
from app.movies.service import (
    UnknownGenresError,
    create_movie,
    create_review,
    delete_movie,
    get_movie,
    list_genres,
    list_movies,
    list_reviews,
    search_directors,
    update_movie,
)

router = APIRouter()
genres_router = APIRouter()
directors_router = APIRouter()

T = TypeVar("T")


async def _cached(key: str, response: Response, compute: Callable[[], Awaitable[T]]) -> T:
    """Devolve o resultado guardado ou o calcula e guarda (plan 101, DEC-4 a DEC-6).

    O cabeçalho X-Cache informa HIT (veio do cache), MISS (calculado agora) ou
    BYPASS (cache desligado).
    """

    if not query_cache.enabled:
        response.headers["X-Cache"] = "BYPASS"
        return await compute()
    cached = query_cache.get(key)
    if cached is not MISSING:
        response.headers["X-Cache"] = "HIT"
        return cast(T, cached)  # guardado por esta mesma chave, com o mesmo tipo
    # Anotada antes de ir ao banco: se uma escrita limpar o cache no meio da
    # consulta, o resultado (talvez velho) não é guardado.
    generation = query_cache.generation
    value = await compute()
    query_cache.set(key, value, generation)
    response.headers["X-Cache"] = "MISS"
    return value


def _catalog_key(query: CatalogQuery) -> str:
    """Chave do cache para uma consulta do catálogo já validada (plan 101, DEC-2).

    Gêneros e status são ordenados: a mesma escolha em outra ordem usa a mesma entrada.
    """

    data = query.model_dump(mode="json")
    data["genre"] = sorted(data["genre"])
    data["status"] = sorted(data["status"])
    return "movies:" + json.dumps(data, sort_keys=True, ensure_ascii=False)


@router.get(
    "",
    response_model=Page[MovieListItem],
    summary="Lista o catálogo paginado, com busca, filtros e ordenação",
)
async def get_movies(
    # Um modelo reúne os parâmetros da URL e as validações cruzadas (plan 100, DEC-2).
    query: Annotated[CatalogQuery, Query()],
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Page[MovieListItem]:
    return await _cached(
        _catalog_key(query),
        response,
        lambda: list_movies(
            db,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            filters=query.filters(),
        ),
    )


MOVIE_NOT_FOUND = "Filme não encontrado."


@router.get(
    "/{sk_movie_id}",
    response_model=MovieDetail,
    summary="Detalhes de um filme",
    responses={404: {"description": MOVIE_NOT_FOUND}},
)
async def read_movie(sk_movie_id: str, db: AsyncSession = Depends(get_db)) -> MovieDetail:
    movie = await get_movie(db, sk_movie_id)
    if movie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MOVIE_NOT_FOUND)
    return movie


@router.get(
    "/{sk_movie_id}/reviews",
    response_model=Page[ReviewItem],
    summary="Avaliações de um filme, das mais recentes para as mais antigas",
    responses={404: {"description": MOVIE_NOT_FOUND}},
)
async def read_movie_reviews(
    sk_movie_id: str,
    page: int = Query(1, ge=1, description="Página, começando em 1."),
    page_size: int = Query(10, ge=1, le=100, description="Avaliações por página (1 a 100)."),
    db: AsyncSession = Depends(get_db),
) -> Page[ReviewItem]:
    reviews = await list_reviews(db, sk_movie_id, page=page, page_size=page_size)
    if reviews is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MOVIE_NOT_FOUND)
    return reviews


@genres_router.get("", response_model=list[str], summary="Gêneros cadastrados, em ordem alfabética")
async def read_genres(response: Response, db: AsyncSession = Depends(get_db)) -> list[str]:
    return await _cached("genres", response, lambda: list_genres(db))


@directors_router.get(
    "", response_model=list[str], summary="Sugestões de diretores pelo nome (até 10)"
)
async def read_directors(
    search: str = Query(
        ...,
        min_length=2,
        max_length=255,
        description="Parte do nome; não diferencia acentos nem maiúsculas.",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    return await search_directors(db, search)


def _genres_error(error: UnknownGenresError) -> RequestValidationError:
    """Gênero inexistente vira um 422 no campo `generos`, como os demais erros de campo."""

    return RequestValidationError(
        [{"loc": ("body", "generos"), "msg": str(error), "type": "value_error"}]
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MovieDetail,
    summary="Cadastra um filme",
)
async def post_movie(data: MovieInput, db: AsyncSession = Depends(get_db)) -> MovieDetail:
    try:
        return await create_movie(db, data)
    except UnknownGenresError as error:
        raise _genres_error(error) from None


@router.put(
    "/{sk_movie_id}",
    response_model=MovieDetail,
    summary="Atualiza os dados editáveis de um filme",
    responses={404: {"description": MOVIE_NOT_FOUND}},
)
async def put_movie(
    sk_movie_id: str, data: MovieInput, db: AsyncSession = Depends(get_db)
) -> MovieDetail:
    try:
        movie = await update_movie(db, sk_movie_id, data)
    except UnknownGenresError as error:
        raise _genres_error(error) from None
    if movie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MOVIE_NOT_FOUND)
    return movie


@router.delete(
    "/{sk_movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove um filme definitivamente, com avaliações, vínculos e métricas",
    responses={404: {"description": MOVIE_NOT_FOUND}},
)
async def remove_movie(sk_movie_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    if not await delete_movie(db, sk_movie_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MOVIE_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{sk_movie_id}/reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewItem,
    summary="Adiciona uma avaliação (1 a 5 estrelas) a um filme",
    responses={404: {"description": MOVIE_NOT_FOUND}},
)
async def post_review(
    sk_movie_id: str, data: ReviewInput, db: AsyncSession = Depends(get_db)
) -> ReviewItem:
    review = await create_review(db, sk_movie_id, data)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MOVIE_NOT_FOUND)
    return review
