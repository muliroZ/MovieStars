"""Testes do cache de consultas pela API (feature 101).

O `conftest.py` esvazia o cache antes de cada teste.
"""

import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import query_cache
from app.movies import router
from app.movies.models import DimGenre
from tests.helpers import add_movie

MOVIES = "/api/v1/movies"


async def seed(session: AsyncSession) -> None:
    """Três filmes com gêneros, status e notas diferentes."""

    drama, horror = DimGenre(nome_genero="Drama"), DimGenre(nome_genero="Horror")
    await add_movie(
        session, "Alfa", 2018, status_filme="Lançado", genres=[drama, horror], notas=[8.0]
    )
    await add_movie(session, "Bravo", 2020, status_filme="Planejado", genres=[drama], notas=[4.0])
    await add_movie(session, "Charlie", 2022, status_filme="Lançado", genres=[horror])


async def cache_header(client: AsyncClient, url: str) -> str | None:
    response = await client.get(url)
    assert response.status_code == 200
    return response.headers.get("x-cache")


# --- T-04: GET /movies (CA-1 a CA-3, CA-5, CA-7, CA-15, CA-17) ---


async def test_same_query_twice_is_miss_then_hit(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed(session)
    url = f"{MOVIES}?sort=rating&genre=Drama"

    first = await client.get(url)
    second = await client.get(url)

    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    assert second.json() == first.json()
    assert [item["titulo"] for item in second.json()["items"]] == ["Alfa", "Bravo"]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("genre=Drama&genre=Horror", "genre=Horror&genre=Drama"),
        ("status=Lançado&status=Planejado", "status=Planejado&status=Lançado"),
    ],
)
async def test_list_order_does_not_matter(
    client: AsyncClient, session: AsyncSession, first: str, second: str
) -> None:
    await seed(session)

    assert await cache_header(client, f"{MOVIES}?{first}") == "MISS"
    assert await cache_header(client, f"{MOVIES}?{second}") == "HIT"


@pytest.mark.parametrize(
    "changed",
    [
        "page=2",
        "page_size=10",
        "search=alf",
        "genre=Horror",
        "genre_mode=all",
        "year_min=2019",
        "status=Planejado",
        "reviews=with",
        "min_stars=3",
        "sort=year",
        "reverse=true",
    ],
)
async def test_any_other_difference_is_another_entry(
    client: AsyncClient, session: AsyncSession, changed: str
) -> None:
    await seed(session)
    base = f"{MOVIES}?genre=Drama"

    assert await cache_header(client, base) == "MISS"
    assert await cache_header(client, f"{base}&{changed}") == "MISS"
    assert await cache_header(client, base) == "HIT"


async def test_equivalent_values_share_the_entry(client: AsyncClient) -> None:
    # A chave vem do modelo validado: reverse=1 e reverse=true são o mesmo valor.
    assert await cache_header(client, f"{MOVIES}?reverse=true") == "MISS"
    assert await cache_header(client, f"{MOVIES}?reverse=1") == "HIT"


async def test_invalid_query_is_not_cached(client: AsyncClient) -> None:
    invalid = await client.get(f"{MOVIES}?min_stars=9")

    assert invalid.status_code == 422
    assert "x-cache" not in invalid.headers
    assert await cache_header(client, f"{MOVIES}?min_stars=5") == "MISS"


async def test_disabled_cache_is_bypassed(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed(session)
    monkeypatch.setattr(query_cache, "enabled", False)

    assert await cache_header(client, MOVIES) == "BYPASS"
    assert await cache_header(client, MOVIES) == "BYPASS"
    assert len(query_cache) == 0


async def test_same_body_with_cache_on_and_off(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed(session)
    url = f"{MOVIES}?sort=rating&reverse=true"

    await client.get(url)  # MISS
    cached = await client.get(url)  # HIT
    monkeypatch.setattr(query_cache, "enabled", False)
    bypassed = await client.get(url)

    assert cached.headers["x-cache"] == "HIT"
    assert bypassed.headers["x-cache"] == "BYPASS"
    assert (cached.status_code, cached.json()) == (bypassed.status_code, bypassed.json())


# --- T-05: GET /genres e rotas sem cache (CA-4, CA-6, CA-7) ---


async def test_genres_miss_then_hit(client: AsyncClient, session: AsyncSession) -> None:
    await seed(session)

    first = await client.get("/api/v1/genres")
    second = await client.get("/api/v1/genres")

    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    assert second.json() == first.json() == ["Drama", "Horror"]


async def test_other_routes_do_not_use_cache(client: AsyncClient, session: AsyncSession) -> None:
    await seed(session)
    movie_id = (await client.get(MOVIES)).json()["items"][0]["sk_movie_id"]

    for url in (
        f"{MOVIES}/{movie_id}",
        f"{MOVIES}/{movie_id}/reviews",
        "/api/v1/directors?search=an",
    ):
        response = await client.get(url)
        assert response.status_code == 200, url
        assert "x-cache" not in response.headers, url


# --- T-06: limpeza nas escritas (CA-8 a CA-11) ---

VALID_MOVIE = {"titulo": "Delta", "ano_lancamento": 2021, "status_filme": "Lançado"}
VALID_REVIEW = {"nome": "Ana Souza", "estrelas": 5, "comentario": "Ótimo filme."}


async def movie_ids(client: AsyncClient) -> dict[str, str]:
    """Título → chave, lidos com o cache desligado para não mexer no que está guardado."""

    enabled = query_cache.enabled
    query_cache.enabled = False
    try:
        items = (await client.get(MOVIES)).json()["items"]
    finally:
        query_cache.enabled = enabled
    return {item["titulo"]: item["sk_movie_id"] for item in items}


async def test_new_review_refreshes_rating_order_and_filter(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed(session)
    ids = await movie_ids(client)
    by_rating, min_four = f"{MOVIES}?sort=rating", f"{MOVIES}?min_stars=4"
    before = (await client.get(by_rating)).json()
    await client.get(min_four)
    assert [item["titulo"] for item in before["items"]] == ["Alfa", "Bravo", "Charlie"]
    assert await cache_header(client, by_rating) == "HIT"

    response = await client.post(f"{MOVIES}/{ids['Charlie']}/reviews", json=VALID_REVIEW)
    assert response.status_code == 201

    after = await client.get(by_rating)
    assert after.headers["x-cache"] == "MISS"
    charlie = after.json()["items"][0]
    assert (charlie["titulo"], charlie["media_estrelas"], charlie["qtd_avaliacoes"]) == (
        "Charlie",
        5.0,
        1,
    )
    assert [item["titulo"] for item in after.json()["items"]] == ["Charlie", "Alfa", "Bravo"]
    filtered = await client.get(min_four)
    assert filtered.headers["x-cache"] == "MISS"
    assert [item["titulo"] for item in filtered.json()["items"]] == ["Alfa", "Charlie"]


async def test_create_update_and_delete_refresh_the_catalog(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed(session)
    ids = await movie_ids(client)

    async def titles_after_write() -> tuple[str | None, list[str], int]:
        response = await client.get(MOVIES)
        body = response.json()
        return response.headers.get("x-cache"), [i["titulo"] for i in body["items"]], body["total"]

    await client.get(MOVIES)
    assert (await client.post(MOVIES, json=VALID_MOVIE)).status_code == 201
    assert await titles_after_write() == ("MISS", ["Alfa", "Bravo", "Charlie", "Delta"], 4)

    await client.get(MOVIES)
    updated = {**VALID_MOVIE, "titulo": "Zulu", "ano_lancamento": 2018}
    assert (await client.put(f"{MOVIES}/{ids['Alfa']}", json=updated)).status_code == 200
    assert await titles_after_write() == ("MISS", ["Bravo", "Charlie", "Delta", "Zulu"], 4)

    await client.get(MOVIES)
    assert (await client.delete(f"{MOVIES}/{ids['Bravo']}")).status_code == 204
    assert await titles_after_write() == ("MISS", ["Charlie", "Delta", "Zulu"], 3)


async def test_write_discards_every_entry(client: AsyncClient, session: AsyncSession) -> None:
    await seed(session)
    ids = await movie_ids(client)
    unrelated = f"{MOVIES}?search=charlie"
    await client.get("/api/v1/genres")
    await client.get(unrelated)

    await client.post(f"{MOVIES}/{ids['Alfa']}/reviews", json=VALID_REVIEW)

    assert len(query_cache) == 0
    assert await cache_header(client, "/api/v1/genres") == "MISS"
    assert await cache_header(client, unrelated) == "MISS"


async def test_failed_writes_keep_the_cache(client: AsyncClient, session: AsyncSession) -> None:
    await seed(session)
    missing = f"{MOVIES}/nao-existe"
    await client.get(MOVIES)

    failures = [
        await client.post(f"{missing}/reviews", json=VALID_REVIEW),
        await client.post(MOVIES, json={**VALID_MOVIE, "generos": ["Inexistente"]}),
        await client.post(MOVIES, json={**VALID_MOVIE, "titulo": ""}),
        await client.put(missing, json=VALID_MOVIE),
        await client.delete(missing),
    ]

    assert [response.status_code for response in failures] == [404, 422, 422, 404, 404]
    assert await cache_header(client, MOVIES) == "HIT"


# --- T-07: corrida, expiração e limite (CA-12 a CA-14) ---


async def test_query_during_a_write_is_not_stored(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed(session)
    original = router.list_movies

    async def list_movies_with_concurrent_write(*args: object, **kwargs: object) -> BaseModel:
        result = await original(*args, **kwargs)
        query_cache.clear()  # uma escrita termina enquanto a consulta ainda não respondeu
        return result

    monkeypatch.setattr(router, "list_movies", list_movies_with_concurrent_write)
    assert await cache_header(client, MOVIES) == "MISS"
    assert len(query_cache) == 0

    monkeypatch.setattr(router, "list_movies", original)
    assert await cache_header(client, MOVIES) == "MISS"
    assert await cache_header(client, MOVIES) == "HIT"


async def test_entry_expires_after_300_seconds(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed(session)
    now = [1000.0]
    monkeypatch.setattr(query_cache, "clock", lambda: now[0])

    assert await cache_header(client, MOVIES) == "MISS"
    now[0] += 299
    assert await cache_header(client, MOVIES) == "HIT"
    now[0] += 1
    assert await cache_header(client, MOVIES) == "MISS"


async def test_least_recently_used_query_leaves_first(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed(session)
    monkeypatch.setattr(query_cache, "max_entries", 2)
    first, second, third = (f"{MOVIES}?page_size={size}" for size in (10, 20, 30))

    for url in (first, second, third):
        assert await cache_header(client, url) == "MISS"

    assert await cache_header(client, third) == "HIT"
    assert await cache_header(client, second) == "HIT"
    assert await cache_header(client, first) == "MISS"
