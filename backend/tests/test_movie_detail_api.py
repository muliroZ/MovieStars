from datetime import date, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import DimCompany, DimGenre, DimPerson, FactMoviePerformance, MovieReview
from app.movies.service import get_movie
from tests.helpers import add_movie


def performance(**values: Decimal | None) -> FactMoviePerformance:
    """Métricas com lucro 0 por padrão (as colunas de lucro são obrigatórias)."""

    return FactMoviePerformance(**{"lucro_brl": Decimal(0), "lucro_usd": Decimal(0), **values})


# --- T-02: get_movie (CA-4, CA-5, CA-7, CA-8, CA-10 a CA-13, CA-15) ---


async def test_get_movie_returns_basic_fields_and_sorted_lists(session: AsyncSession) -> None:
    movie = await add_movie(
        session,
        "Rings",
        2017,
        data_lancamento=date(2017, 2, 1),
        duracao_minutos=102,
        status_filme="Lançado",
        sinopse="Julia fica preocupada.",
        url_poster="https://exemplo.com/p.jpg",
        url_backdrop="https://exemplo.com/b.jpg",
        genres=[DimGenre(nome_genero="Horror"), DimGenre(nome_genero="Drama")],
        companies=[DimCompany(nome_produtora="Zeta"), DimCompany(nome_produtora="Alfa")],
        people=[
            DimPerson(nome_pessoa="Zé", tipo_pessoa="Diretor"),
            DimPerson(nome_pessoa="Ana", tipo_pessoa="Diretor"),
            DimPerson(nome_pessoa="Rui", tipo_pessoa="Roteirista"),
            DimPerson(nome_pessoa="Matilda", tipo_pessoa="Ator"),
            DimPerson(nome_pessoa="Alex", tipo_pessoa="Ator"),
        ],
        notas=[9.0, 6.0],
    )

    detail = await get_movie(session, movie.sk_movie_id)

    assert detail is not None
    assert (detail.titulo, detail.ano_lancamento, detail.data_lancamento) == (
        "Rings",
        2017,
        date(2017, 2, 1),
    )
    assert (detail.duracao_minutos, detail.status_filme, detail.sinopse) == (
        102,
        "Lançado",
        "Julia fica preocupada.",
    )
    assert detail.url_backdrop == "https://exemplo.com/b.jpg"
    assert detail.generos == ["Drama", "Horror"]
    assert detail.produtoras == ["Alfa", "Zeta"]
    assert (detail.diretores, detail.roteiristas, detail.elenco) == (
        ["Ana", "Zé"],
        ["Rui"],
        ["Alex", "Matilda"],
    )
    assert (detail.media_estrelas, detail.qtd_avaliacoes) == (3.8, 2)


async def test_get_movie_with_missing_fields(session: AsyncSession) -> None:
    movie = await add_movie(session, "Só o Título", None)

    detail = await get_movie(session, movie.sk_movie_id)

    assert detail is not None
    assert detail.model_dump(exclude={"sk_movie_id", "titulo"}) == {
        "ano_lancamento": None,
        "data_lancamento": None,
        "duracao_minutos": None,
        "status_filme": None,
        "sinopse": None,
        "url_poster": None,
        "url_backdrop": None,
        "generos": [],
        "diretores": [],
        "roteiristas": [],
        "elenco": [],
        "produtoras": [],
        "financeiro": None,
        "media_estrelas": None,
        "qtd_avaliacoes": 0,
    }


@pytest.mark.parametrize(
    ("values", "expected_usd"),
    [
        (
            {
                "orcamento_usd": Decimal("25000000"),
                "receita_usd": Decimal("83080890"),
                "lucro_usd": Decimal("58080890"),
            },
            (25000000.0, 83080890.0, 58080890.0),
        ),
        (  # só orçamento: o lucro gravado (−orçamento) não é exibido
            {"orcamento_usd": Decimal("7500000"), "lucro_usd": Decimal("-7500000")},
            (7500000.0, None, None),
        ),
        ({}, (None, None, None)),  # nenhum: o lucro gravado (0) não é exibido
    ],
)
async def test_get_movie_financials_show_profit_only_with_budget_and_revenue(
    session: AsyncSession, values: dict, expected_usd: tuple
) -> None:
    movie = await add_movie(session, "Com Métricas", performance=performance(**values))

    detail = await get_movie(session, movie.sk_movie_id)

    assert detail is not None and detail.financeiro is not None
    financeiro = detail.financeiro
    assert (financeiro.orcamento_usd, financeiro.receita_usd, financeiro.lucro_usd) == expected_usd


async def test_get_movie_financials_per_currency(session: AsyncSession) -> None:
    movie = await add_movie(
        session,
        "Prejuízo",
        performance=performance(
            orcamento_brl=Decimal("100.50"),
            receita_brl=Decimal("40.25"),
            lucro_brl=Decimal("-60.25"),
        ),
    )

    detail = await get_movie(session, movie.sk_movie_id)

    assert detail is not None and detail.financeiro is not None
    assert (detail.financeiro.lucro_brl, detail.financeiro.lucro_usd) == (-60.25, None)


async def test_get_movie_unknown_returns_none(session: AsyncSession) -> None:
    assert await get_movie(session, "nao-existe") is None


# --- T-03: GET /api/v1/movies/{sk_movie_id} (CA-1, CA-2, CA-3, CA-16) ---


async def test_read_movie_returns_detail(client: AsyncClient, session: AsyncSession) -> None:
    movie = await add_movie(
        session,
        "Rings",
        2017,
        data_lancamento=date(2017, 2, 1),
        genres=[DimGenre(nome_genero="Horror")],
        people=[DimPerson(nome_pessoa="F. Javier Gutiérrez", tipo_pessoa="Diretor")],
        performance=performance(
            orcamento_usd=Decimal("25000000"),
            receita_usd=Decimal("83080890"),
            lucro_usd=Decimal("58080890"),
        ),
        notas=[10.0],
    )

    response = await client.get(f"/api/v1/movies/{movie.sk_movie_id}")

    assert response.status_code == 200
    assert response.json() == {
        "sk_movie_id": movie.sk_movie_id,
        "titulo": "Rings",
        "ano_lancamento": 2017,
        "data_lancamento": "2017-02-01",
        "duracao_minutos": None,
        "status_filme": None,
        "sinopse": None,
        "url_poster": None,
        "url_backdrop": None,
        "generos": ["Horror"],
        "diretores": ["F. Javier Gutiérrez"],
        "roteiristas": [],
        "elenco": [],
        "produtoras": [],
        "financeiro": {
            "orcamento_brl": None,
            "receita_brl": None,
            "lucro_brl": None,
            "orcamento_usd": 25000000.0,
            "receita_usd": 83080890.0,
            "lucro_usd": 58080890.0,
        },
        "media_estrelas": 5.0,
        "qtd_avaliacoes": 1,
    }


async def test_read_movie_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado."}


async def test_detail_average_matches_catalog(client: AsyncClient, session: AsyncSession) -> None:
    movie = await add_movie(session, "Média", notas=[9.7, 3.2, 8.8])

    detail = (await client.get(f"/api/v1/movies/{movie.sk_movie_id}")).json()
    card = (await client.get("/api/v1/movies", params={"search": "média"})).json()["items"][0]

    assert (detail["media_estrelas"], detail["qtd_avaliacoes"]) == (
        card["media_estrelas"],
        card["qtd_avaliacoes"],
    )


# --- T-04: GET /api/v1/movies/{sk_movie_id}/reviews (CA-3, CA-17 a CA-21) ---


def review(key: str, nota: float, when: datetime) -> MovieReview:
    return MovieReview(
        sk_movie_review_id=key, nome=f"Pessoa {key}", nota=nota, comentario="Ok.", created_at=when
    )


async def test_reviews_newest_first_with_stable_ties(
    client: AsyncClient, session: AsyncSession
) -> None:
    same_day = datetime(2026, 9, 26, 20, 56, 13)
    movie = await add_movie(
        session,
        "Avaliado",
        reviews=[
            review("b", 5.0, same_day),
            review("a", 6.0, same_day),
            review("novo", 9.8, datetime(2026, 10, 1, 1, 30)),
        ],
    )

    response = await client.get(f"/api/v1/movies/{movie.sk_movie_id}/reviews")

    items = response.json()["items"]
    assert [item["sk_movie_review_id"] for item in items] == ["novo", "a", "b"]
    assert items[0] == {
        "sk_movie_review_id": "novo",
        "nome": "Pessoa novo",
        "estrelas": 4.9,
        "comentario": "Ok.",
        "created_at": "2026-10-01T01:30:00Z",
    }


async def test_reviews_are_paginated_by_ten(client: AsyncClient, session: AsyncSession) -> None:
    movie = await add_movie(session, "Muitas", notas=[float(n % 11) for n in range(13)])
    url = f"/api/v1/movies/{movie.sk_movie_id}/reviews"

    first = (await client.get(url)).json()
    second = (await client.get(url, params={"page": 2})).json()
    beyond = (await client.get(url, params={"page": 3})).json()

    assert (len(first["items"]), first["total"], first["pages"], first["page_size"]) == (
        10,
        13,
        2,
        10,
    )
    assert len(second["items"]) == 3
    all_keys = [item["sk_movie_review_id"] for item in first["items"] + second["items"]]
    assert len(set(all_keys)) == 13
    assert (beyond["items"], beyond["total"]) == ([], 13)


async def test_reviews_of_movie_without_reviews(client: AsyncClient, session: AsyncSession) -> None:
    movie = await add_movie(session, "Sem Avaliações")

    body = (await client.get(f"/api/v1/movies/{movie.sk_movie_id}/reviews")).json()

    assert (body["items"], body["total"], body["pages"]) == ([], 0, 0)


async def test_reviews_of_unknown_movie_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies/nao-existe/reviews")

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado."}


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
async def test_reviews_reject_invalid_params(
    client: AsyncClient, session: AsyncSession, params: dict
) -> None:
    movie = await add_movie(session, "Qualquer")

    response = await client.get(f"/api/v1/movies/{movie.sk_movie_id}/reviews", params=params)

    assert response.status_code == 422
