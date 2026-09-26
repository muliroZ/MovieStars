"""Rotas HTTP do domínio de filmes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.movies.schemas import MoviePage
from app.movies.service import list_movies

router = APIRouter()


@router.get("", response_model=MoviePage, summary="Lista o catálogo paginado")
async def get_movies(
    page: int = Query(1, ge=1, description="Página, começando em 1."),
    page_size: int = Query(20, ge=1, le=100, description="Filmes por página (1 a 100)."),
    search: str = Query(
        "",
        max_length=200,
        description="Parte do título; não diferencia acentos nem maiúsculas.",
    ),
    db: AsyncSession = Depends(get_db),
) -> MoviePage:
    return await list_movies(db, page=page, page_size=page_size, search=search)
