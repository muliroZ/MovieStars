"""Rotas HTTP do domínio de filmes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies.schemas import MovieDetail, MovieListItem, Page, ReviewItem
from app.movies.service import get_movie, list_movies, list_reviews

router = APIRouter()


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
