from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import DimGenre, DimMovie, DimPerson, MovieReview
from app.movies.service import list_movies


async def add_movie(
    session: AsyncSession,
    titulo: str,
    ano: int | None = 2000,
    *,
    genres: list[DimGenre] | None = None,
    people: list[DimPerson] | None = None,
    notas: list[float] | None = None,
) -> DimMovie:
    """Insere um filme pelo ORM (a chave e o id_filme são gerados)."""

    movie = DimMovie(
        id_filme=uuid4().hex,
        titulo=titulo,
        ano_lancamento=ano,
        genres=genres or [],
        people=people or [],
        reviews=[
            MovieReview(nome="Ana", nota=nota, comentario="Comentário.") for nota in notas or []
        ],
    )
    session.add(movie)
    await session.commit()
    return movie


def titles(page) -> list[str]:
    return [item.titulo for item in page.items]


# --- T-04: fixtures ---


async def test_client_uses_temporary_empty_database(
    client: AsyncClient, session: AsyncSession
) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert await session.scalar(select(func.count()).select_from(DimMovie)) == 0


# --- T-05: listagem paginada e ordenada (CA-1, CA-2, CA-3, CA-24) ---


async def test_list_movies_paginates(session: AsyncSession) -> None:
    for number in range(25):
        await add_movie(session, f"Filme {number:02d}")

    first = await list_movies(session, page=1, page_size=20)
    second = await list_movies(session, page=2, page_size=20)
    beyond = await list_movies(session, page=3, page_size=20)

    assert (len(first.items), first.total, first.pages, first.page, first.page_size) == (
        20,
        25,
        2,
        1,
        20,
    )
    assert titles(second) == [f"Filme {number}" for number in range(20, 25)]
    assert (beyond.items, beyond.total, beyond.pages, beyond.page) == ([], 25, 2, 3)


async def test_list_movies_on_empty_catalog(session: AsyncSession) -> None:
    page = await list_movies(session, page=1, page_size=20)

    assert (page.items, page.total, page.pages) == ([], 0, 0)


async def test_list_movies_orders_ignoring_accents_and_case(session: AsyncSession) -> None:
    for titulo in ["Abc", "À La Recherche", "a dark place", "Zorro", "Émile"]:
        await add_movie(session, titulo)

    page = await list_movies(session, page=1, page_size=20)

    assert titles(page) == ["a dark place", "À La Recherche", "Abc", "Émile", "Zorro"]


async def test_list_movies_orders_same_title_by_year(session: AsyncSession) -> None:
    await add_movie(session, "Rings", 2017)
    await add_movie(session, "Rings", 2005)

    page = await list_movies(session, page=1, page_size=20)

    assert [item.ano_lancamento for item in page.items] == [2005, 2017]


async def test_list_movies_order_is_stable_between_pages(session: AsyncSession) -> None:
    for _ in range(5):
        await add_movie(session, "Mesmo Título", 2000)

    pages = [await list_movies(session, page=number, page_size=2) for number in (1, 2, 3)]
    keys = [item.sk_movie_id for page in pages for item in page.items]

    assert len(keys) == len(set(keys)) == 5


# --- T-06: busca (CA-10, CA-11, CA-12, CA-13, CA-15) ---


async def test_search_matches_any_part_of_title(session: AsyncSession) -> None:
    for titulo in ["Rings", "The Lord of the Rings", "Cidade de Deus"]:
        await add_movie(session, titulo)

    page = await list_movies(session, page=1, page_size=20, search="ring")

    assert titles(page) == ["Rings", "The Lord of the Rings"]
    assert page.total == 2


async def test_search_ignores_accents_and_case(session: AsyncSession) -> None:
    await add_movie(session, "Ação Total")
    await add_movie(session, "Outro Filme")

    results = [
        titles(await list_movies(session, page=1, page_size=20, search=term))
        for term in ["acao", "AÇÃO", "Ação"]
    ]

    assert results == [["Ação Total"]] * 3


async def test_search_trims_spaces_and_blank_means_no_filter(session: AsyncSession) -> None:
    await add_movie(session, "Rings")
    await add_movie(session, "Cidade de Deus")

    trimmed = await list_movies(session, page=1, page_size=20, search="  ring  ")
    blank = await list_movies(session, page=1, page_size=20, search="   ")

    assert titles(trimmed) == ["Rings"]
    assert blank.total == 2


async def test_search_treats_like_wildcards_as_text(session: AsyncSession) -> None:
    for titulo in ["100% Lobo", "1000 Dias", "a_b", "axb"]:
        await add_movie(session, titulo)

    percent = await list_movies(session, page=1, page_size=20, search="100%")
    underscore = await list_movies(session, page=1, page_size=20, search="a_b")

    assert titles(percent) == ["100% Lobo"]
    assert titles(underscore) == ["a_b"]


async def test_search_results_are_paginated_and_ordered(session: AsyncSession) -> None:
    for number in range(5):
        await add_movie(session, f"Ring {4 - number}")
    await add_movie(session, "Sem Relação")

    first = await list_movies(session, page=1, page_size=2, search="ring")
    last = await list_movies(session, page=3, page_size=2, search="ring")

    assert (titles(first), first.total, first.pages) == (["Ring 0", "Ring 1"], 5, 3)
    assert titles(last) == ["Ring 4"]


# --- T-07: média, gêneros e diretores (CA-6, CA-7) ---


async def test_list_movies_includes_star_average_and_count(session: AsyncSession) -> None:
    await add_movie(session, "Avaliado", notas=[9.0, 6.0])
    await add_movie(session, "Sem Avaliações")

    rated, unrated = (await list_movies(session, page=1, page_size=20)).items

    assert (rated.media_estrelas, rated.qtd_avaliacoes) == (3.8, 2)
    assert (unrated.media_estrelas, unrated.qtd_avaliacoes) == (None, 0)


async def test_list_movies_includes_sorted_genres_and_only_directors(
    session: AsyncSession,
) -> None:
    drama, action = DimGenre(nome_genero="Drama"), DimGenre(nome_genero="Action")
    people = [
        DimPerson(nome_pessoa="Zé Diretor", tipo_pessoa="Diretor"),
        DimPerson(nome_pessoa="Ana Diretora", tipo_pessoa="Diretor"),
        DimPerson(nome_pessoa="Beto Ator", tipo_pessoa="Ator"),
        DimPerson(nome_pessoa="Caio Roteirista", tipo_pessoa="Roteirista"),
    ]
    await add_movie(session, "Completo", genres=[drama, action], people=people)
    await add_movie(session, "Vazio")

    complete, empty = (await list_movies(session, page=1, page_size=20)).items

    assert complete.generos == ["Action", "Drama"]
    assert complete.diretores == ["Ana Diretora", "Zé Diretor"]
    assert (empty.generos, empty.diretores) == ([], [])


# --- T-08: rota GET /api/v1/movies (CA-1, CA-25, CA-26) ---


async def test_get_movies_returns_page(client: AsyncClient, session: AsyncSession) -> None:
    drama = DimGenre(nome_genero="Drama")
    director = DimPerson(nome_pessoa="Fernando Meirelles", tipo_pessoa="Diretor")
    movie = await add_movie(
        session, "Cidade de Deus", 2002, genres=[drama], people=[director], notas=[10.0, 9.0]
    )

    response = await client.get("/api/v1/movies", params={"search": "cidade"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "sk_movie_id": movie.sk_movie_id,
                "titulo": "Cidade de Deus",
                "ano_lancamento": 2002,
                "url_poster": None,
                "media_estrelas": 4.8,
                "qtd_avaliacoes": 2,
                "generos": ["Drama"],
                "diretores": ["Fernando Meirelles"],
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "pages": 1,
    }


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}, {"search": "x" * 201}],
)
async def test_get_movies_rejects_invalid_params(client: AsyncClient, params: dict) -> None:
    response = await client.get("/api/v1/movies", params=params)

    assert response.status_code == 422


async def test_get_movies_accepts_search_with_200_characters(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies", params={"search": "x" * 200})

    assert response.status_code == 200
    assert response.json()["total"] == 0
