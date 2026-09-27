from datetime import date

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import DimGenre
from app.movies.schemas import CatalogFilters, CatalogQuery
from app.movies.service import list_movies
from tests.helpers import add_movie

MAX_YEAR = date.today().year + 10

# --- T-03: CatalogFilters e CatalogQuery (CA-5 a CA-8, CA-13, CA-14, CA-21) ---


def errors_of(data: dict) -> dict[str, str]:
    with pytest.raises(ValidationError) as error:
        CatalogFilters.model_validate(data)
    return {
        str(item["loc"][0]): str(item["msg"]).removeprefix("Value error, ")
        for item in error.value.errors()
    }


def test_catalog_filters_defaults() -> None:
    filters = CatalogFilters()

    assert filters.model_dump() == {
        "genre": [],
        "genre_mode": "any",
        "year_min": None,
        "year_max": None,
        "status": [],
        "reviews": "all",
        "min_stars": None,
        "sort": "title",
        "reverse": False,
    }


def test_catalog_filters_accepts_full_combination() -> None:
    filters = CatalogFilters.model_validate(
        {
            "genre": ["Drama", "Horror"],
            "genre_mode": "all",
            "year_min": 2018,
            "year_max": 2018,
            "status": ["Lançado", "Planejado"],
            "reviews": "with",
            "min_stars": 5,
            "sort": "rating",
            "reverse": True,
        }
    )

    assert (filters.genre, filters.status) == (["Drama", "Horror"], ["Lançado", "Planejado"])
    assert (filters.year_min, filters.year_max, filters.min_stars) == (2018, 2018, 5)


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"genre_mode": "some"}, "genre_mode"),
        ({"status": ["Cancelado"]}, "status"),
        ({"reviews": "maybe"}, "reviews"),
        ({"sort": "popularity"}, "sort"),
        ({"min_stars": 0}, "min_stars"),
        ({"min_stars": 6}, "min_stars"),
        ({"year_min": "abc"}, "year_min"),
    ],
)
def test_catalog_filters_rejects_invalid(data: dict, field: str) -> None:
    assert field in errors_of(data)


def test_catalog_filters_year_messages() -> None:
    assert errors_of({"year_min": 1887}) == {"year_min": f"Deve estar entre 1888 e {MAX_YEAR}."}
    assert errors_of({"year_max": MAX_YEAR + 1}) == {
        "year_max": f"Deve estar entre 1888 e {MAX_YEAR}."
    }
    assert errors_of({"year_min": 2025, "year_max": 2020}) == {
        "year_max": "O ano inicial deve ser menor ou igual ao final."
    }


def test_catalog_query_splits_filters() -> None:
    query = CatalogQuery.model_validate({"page": 3, "search": "ring", "genre": ["Drama"]})

    assert (query.page, query.page_size, query.search) == (3, 20, "ring")
    assert query.filters() == CatalogFilters(genre=["Drama"])


# --- T-04: filtros no list_movies (CA-3 a CA-10) ---


async def seed_catalog(session: AsyncSession) -> None:
    """Quatro filmes com gêneros, anos, status e médias escolhidos para os filtros."""

    drama, horror = DimGenre(nome_genero="Drama"), DimGenre(nome_genero="Horror")
    # nota 7.92 → 3,96 estrelas → exibida 4,0; nota 7.88 → 3,94 → exibida 3,9
    await add_movie(
        session, "Alfa", 2018, status_filme="Lançado", genres=[drama, horror], notas=[7.92]
    )
    await add_movie(session, "Bravo", 2020, status_filme="Planejado", genres=[drama], notas=[7.88])
    await add_movie(session, "Charlie", 2022, status_filme="Lançado", genres=[horror])
    await add_movie(session, "Delta", 2016, status_filme="Em Produção", notas=[10.0])


async def titles_with(session: AsyncSession, search: str = "", **filters: object) -> list[str]:
    page = await list_movies(
        session, page=1, page_size=20, search=search, filters=CatalogFilters(**filters)
    )
    return [item.titulo for item in page.items]


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"genre": ["Drama", "Horror"]}, ["Alfa", "Bravo", "Charlie"]),
        ({"genre": ["Drama", "Horror"], "genre_mode": "all"}, ["Alfa"]),
        ({"genre": ["Drama", "Drama"], "genre_mode": "all"}, ["Alfa", "Bravo"]),
        ({"genre": ["Drama", "Inexistente"], "genre_mode": "all"}, []),
        ({"genre": ["Inexistente", "Horror"]}, ["Alfa", "Charlie"]),
        ({"year_min": 2020}, ["Bravo", "Charlie"]),
        ({"year_max": 2018}, ["Alfa", "Delta"]),
        ({"year_min": 2018, "year_max": 2020}, ["Alfa", "Bravo"]),
        ({"status": ["Lançado", "Planejado"]}, ["Alfa", "Bravo", "Charlie"]),
        ({"reviews": "with"}, ["Alfa", "Bravo", "Delta"]),
        ({"reviews": "without"}, ["Charlie"]),
        ({"min_stars": 4}, ["Alfa", "Delta"]),
        ({"min_stars": 5}, ["Delta"]),
        ({"reviews": "without", "min_stars": 1}, []),
    ],
)
async def test_each_filter(session: AsyncSession, filters: dict, expected: list[str]) -> None:
    await seed_catalog(session)

    assert await titles_with(session, **filters) == expected


async def test_movie_without_genre_never_matches_genre_filter(session: AsyncSession) -> None:
    await seed_catalog(session)

    every_genre = await titles_with(session, genre=["Drama", "Horror"])

    assert "Delta" not in every_genre


async def test_filters_combine_with_search_and_counts(session: AsyncSession) -> None:
    await seed_catalog(session)

    page = await list_movies(
        session,
        page=1,
        page_size=20,
        search="LF",
        filters=CatalogFilters(genre=["Drama"], min_stars=4, status=["Lançado"]),
    )

    assert [item.titulo for item in page.items] == ["Alfa"]
    assert (page.total, page.pages) == (1, 1)


async def test_no_filters_behaves_like_feature_001(session: AsyncSession) -> None:
    await seed_catalog(session)

    default = await list_movies(session, page=1, page_size=20)
    explicit = await list_movies(session, page=1, page_size=20, filters=CatalogFilters())

    assert default == explicit
    assert [item.titulo for item in default.items] == ["Alfa", "Bravo", "Charlie", "Delta"]


# --- T-05: ordenação no list_movies (CA-13 a CA-16) ---


async def seed_for_sorting(session: AsyncSession) -> None:
    await add_movie(session, "Beta", 2019, notas=[8.0])  # 4,0 estrelas, 1 avaliação
    await add_movie(session, "Alpha", 2019, notas=[6.0, 4.0])  # 2,5 estrelas, 2 avaliações
    await add_movie(session, "Gama", None)  # sem ano, sem avaliação
    await add_movie(session, "Delta", 2021, notas=[10.0])  # 5,0 estrelas, 1 avaliação
    await add_movie(session, "Épsilon", 2017)  # sem avaliação


@pytest.mark.parametrize(
    ("sort", "reverse", "expected"),
    [
        ("title", False, ["Alpha", "Beta", "Delta", "Épsilon", "Gama"]),
        ("title", True, ["Gama", "Épsilon", "Delta", "Beta", "Alpha"]),
        # sem ano sempre no fim; empate de ano pelo título
        ("year", False, ["Delta", "Alpha", "Beta", "Épsilon", "Gama"]),
        ("year", True, ["Épsilon", "Alpha", "Beta", "Delta", "Gama"]),
        # sem avaliação sempre no fim, nas duas direções
        ("rating", False, ["Delta", "Beta", "Alpha", "Épsilon", "Gama"]),
        ("rating", True, ["Alpha", "Beta", "Delta", "Épsilon", "Gama"]),
        # quantidade: sem avaliação conta 0 e segue a direção
        ("reviews", False, ["Alpha", "Beta", "Delta", "Épsilon", "Gama"]),
        ("reviews", True, ["Épsilon", "Gama", "Beta", "Delta", "Alpha"]),
    ],
)
async def test_sorting(
    session: AsyncSession, sort: str, reverse: bool, expected: list[str]
) -> None:
    await seed_for_sorting(session)

    assert await titles_with(session, sort=sort, reverse=reverse) == expected


async def test_sorted_pages_do_not_repeat(session: AsyncSession) -> None:
    await seed_for_sorting(session)

    keys = []
    for number in (1, 2, 3):
        page = await list_movies(
            session, page=number, page_size=2, filters=CatalogFilters(sort="reviews")
        )
        keys += [item.sk_movie_id for item in page.items]

    assert len(keys) == len(set(keys)) == 5


# --- T-06: GET /api/v1/movies com filtros (CA-19, CA-21) ---


async def test_route_applies_every_parameter(client: AsyncClient, session: AsyncSession) -> None:
    drama, horror = DimGenre(nome_genero="Drama"), DimGenre(nome_genero="Horror")
    await add_movie(
        session, "Ambos Bom", 2019, status_filme="Lançado", genres=[drama, horror], notas=[9.0]
    )
    await add_movie(
        session, "Ambos Fraco", 2020, status_filme="Lançado", genres=[drama, horror], notas=[3.0]
    )
    await add_movie(session, "Só Drama", 2019, status_filme="Lançado", genres=[drama], notas=[10.0])
    await add_movie(
        session, "Ambos Antigo", 2016, status_filme="Lançado", genres=[drama, horror], notas=[8.0]
    )

    response = await client.get(
        "/api/v1/movies",
        params=[
            ("genre", "Drama"),
            ("genre", "Horror"),
            ("genre_mode", "all"),
            ("year_min", "2018"),
            ("status", "Lançado"),
            ("reviews", "with"),
            ("sort", "rating"),
            ("reverse", "true"),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["titulo"] for item in body["items"]] == ["Ambos Fraco", "Ambos Bom"]
    assert (body["total"], body["pages"]) == (2, 1)


async def test_route_without_new_parameters_matches_001(
    client: AsyncClient, session: AsyncSession
) -> None:
    await add_movie(session, "Zorro", 2016)
    await add_movie(session, "Abc", 2017, notas=[6.0])

    body = (await client.get("/api/v1/movies")).json()

    assert [item["titulo"] for item in body["items"]] == ["Abc", "Zorro"]
    assert set(body) == {"items", "total", "page", "page_size", "pages"}


@pytest.mark.parametrize(
    ("params", "field", "message"),
    [
        (
            {"year_min": 2025, "year_max": 2020},
            "year_max",
            "O ano inicial deve ser menor ou igual ao final.",
        ),
        ({"year_min": 1887}, "year_min", f"Deve estar entre 1888 e {MAX_YEAR}."),
        ({"genre_mode": "some"}, "genre_mode", "Valor inválido."),
        ({"status": "Cancelado"}, "status", "Valor inválido."),
        ({"reviews": "maybe"}, "reviews", "Valor inválido."),
        ({"sort": "popularity"}, "sort", "Valor inválido."),
        ({"min_stars": 0}, "min_stars", "Deve ser no mínimo 1."),
        ({"min_stars": 6}, "min_stars", "Deve ser no máximo 5."),
    ],
)
async def test_route_validation_in_portuguese(
    client: AsyncClient, params: dict, field: str, message: str
) -> None:
    response = await client.get("/api/v1/movies", params=params)

    assert response.status_code == 422
    errors = {error["loc"][1]: error["msg"] for error in response.json()["detail"]}
    assert errors.get(field) == message, response.json()
