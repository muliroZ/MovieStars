"""Rotas HTTP do domínio de filmes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies.schemas import MovieDetail, MovieInput, MovieListItem, Page, ReviewItem
from app.movies.service import (
    UnknownGenresError,
    create_movie,
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


@router.get("", response_model=Page[MovieListItem], summary="Lista o catálogo paginado")
async def get_movies(
    page: int = Query(1, ge=1, description="Página, começando em 1."),
    page_size: int = Query(20, ge=1, le=100, description="Filmes por página (1 a 100)."),
    search: str = Query(
        "",
        max_length=200,
        description="Parte do título; não diferencia acentos nem maiúsculas.",
    ),
    db: AsyncSession = Depends(get_db),
) -> Page[MovieListItem]:
    return await list_movies(db, page=page, page_size=page_size, search=search)


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
async def read_genres(db: AsyncSession = Depends(get_db)) -> list[str]:
    return await list_genres(db)


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
