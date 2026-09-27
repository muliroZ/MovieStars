from datetime import datetime

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import DimReview, MovieReview
from app.movies.schemas import ReviewInput
from tests.helpers import add_movie

VALID_REVIEW = {"nome": "Ana Souza", "estrelas": 4, "comentario": "Ótimo filme."}

# --- T-01: ReviewInput (CA-4 a CA-6) ---


def test_review_input_valid_and_trimmed() -> None:
    review = ReviewInput.model_validate(
        {"nome": "  Ana Souza  ", "estrelas": 5, "comentario": "  Adorei.  "}
    )

    assert (review.nome, review.estrelas, review.comentario) == ("Ana Souza", 5, "Adorei.")


def test_review_input_accepts_limits() -> None:
    review = ReviewInput.model_validate(
        {"nome": "n" * 120, "estrelas": 1, "comentario": "c" * 1000}
    )

    assert review.estrelas == 1


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"nome": ""}, "nome"),
        ({"nome": "   "}, "nome"),
        ({"nome": "n" * 121}, "nome"),
        ({"estrelas": None}, "estrelas"),
        ({"estrelas": 0}, "estrelas"),
        ({"estrelas": 6}, "estrelas"),
        ({"estrelas": 4.5}, "estrelas"),
        ({"estrelas": "abc"}, "estrelas"),
        ({"comentario": "   "}, "comentario"),
        ({"comentario": "c" * 1001}, "comentario"),
    ],
)
def test_review_input_rejects_invalid(data: dict, field: str) -> None:
    with pytest.raises(ValidationError) as error:
        ReviewInput.model_validate({**VALID_REVIEW, **data})

    assert [item["loc"][0] for item in error.value.errors()] == [field]


def test_review_input_requires_every_field() -> None:
    with pytest.raises(ValidationError) as error:
        ReviewInput.model_validate({})

    assert {item["loc"][0] for item in error.value.errors()} == {"nome", "estrelas", "comentario"}


# --- T-02: POST /api/v1/movies/{sk_movie_id}/reviews (CA-7, CA-9 a CA-14) ---


def reviews_url(sk_movie_id: str) -> str:
    return f"/api/v1/movies/{sk_movie_id}/reviews"


async def test_post_review_stores_nota_as_double_the_stars(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await add_movie(session, "Avaliável")

    response = await client.post(
        reviews_url(movie.sk_movie_id),
        json={"nome": "  Ana Souza ", "estrelas": 4, "comentario": " Ótimo filme. "},
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["nome"], body["estrelas"], body["comentario"]) == (
        "Ana Souza",
        4.0,
        "Ótimo filme.",
    )
    assert body["created_at"].endswith("Z")
    stored = await session.scalar(
        select(MovieReview.nota).where(MovieReview.sk_movie_review_id == body["sk_movie_review_id"])
    )
    assert stored == 8.0


async def test_new_review_updates_list_and_averages(
    client: AsyncClient, session: AsyncSession
) -> None:
    # avaliações existentes com data anterior, como as importadas (o created_at do
    # SQLite tem precisão de 1 s: criadas no mesmo segundo, empatariam na ordem)
    old_date = datetime(2026, 1, 1, 12, 0)
    movie = await add_movie(
        session,
        "Com Avaliações",
        reviews=[
            MovieReview(nome="Antiga", nota=nota, comentario="Ok.", created_at=old_date)
            for nota in (2.0, 4.0)
        ],
    )
    session.add(DimReview(sk_movie_id=movie.sk_movie_id, qtd_avaliacoes_usuarios=2))
    await session.commit()

    created = await client.post(
        reviews_url(movie.sk_movie_id), json={**VALID_REVIEW, "estrelas": 5}
    )

    reviews = (await client.get(reviews_url(movie.sk_movie_id))).json()
    detail = (await client.get(f"/api/v1/movies/{movie.sk_movie_id}")).json()
    card = (await client.get("/api/v1/movies", params={"search": "com avaliacoes"})).json()
    assert reviews["items"][0]["sk_movie_review_id"] == created.json()["sk_movie_review_id"]
    assert reviews["total"] == 3
    # notas 2, 4 e 10 → média 5,33 → 2,7 estrelas
    assert (detail["media_estrelas"], detail["qtd_avaliacoes"]) == (2.7, 3)
    assert (card["items"][0]["media_estrelas"], card["items"][0]["qtd_avaliacoes"]) == (2.7, 3)
    # o resumo importado não é alterado
    summary = await session.scalar(
        select(DimReview.qtd_avaliacoes_usuarios).where(DimReview.sk_movie_id == movie.sk_movie_id)
    )
    assert summary == 2


async def test_first_review_gives_movie_an_average(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await add_movie(session, "Sem Avaliações")

    await client.post(reviews_url(movie.sk_movie_id), json={**VALID_REVIEW, "estrelas": 3})

    detail = (await client.get(f"/api/v1/movies/{movie.sk_movie_id}")).json()
    assert (detail["media_estrelas"], detail["qtd_avaliacoes"]) == (3.0, 1)


async def test_unreleased_movie_accepts_review(client: AsyncClient, session: AsyncSession) -> None:
    movie = await add_movie(session, "Futuro", 2029, status_filme="Planejado")

    response = await client.post(reviews_url(movie.sk_movie_id), json=VALID_REVIEW)

    assert response.status_code == 201


async def test_post_review_field_errors_in_portuguese(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await add_movie(session, "Qualquer")

    response = await client.post(
        reviews_url(movie.sk_movie_id),
        json={"nome": "   ", "estrelas": 4.5, "comentario": "c" * 1001},
    )

    assert response.status_code == 422
    messages = {error["loc"][1]: error["msg"] for error in response.json()["detail"]}
    assert messages == {
        "nome": "Campo obrigatório.",
        "estrelas": "Deve ser um número inteiro.",
        "comentario": "Deve ter no máximo 1000 caracteres.",
    }


@pytest.mark.parametrize(
    ("estrelas", "message"),
    [
        (0, "Deve ser no mínimo 1."),
        (6, "Deve ser no máximo 5."),
        ("abc", "Deve ser um número inteiro."),
    ],
)
async def test_post_review_star_limits(
    client: AsyncClient, session: AsyncSession, estrelas: object, message: str
) -> None:
    movie = await add_movie(session, "Limites")

    response = await client.post(
        reviews_url(movie.sk_movie_id), json={**VALID_REVIEW, "estrelas": estrelas}
    )

    assert response.json()["detail"] == [
        {"loc": ["body", "estrelas"], "msg": message, "type": response.json()["detail"][0]["type"]}
    ]
    total = await session.scalar(select(func.count()).select_from(MovieReview))
    assert total == 0


async def test_post_review_unknown_movie_returns_404(client: AsyncClient) -> None:
    response = await client.post(reviews_url("nao-existe"), json=VALID_REVIEW)

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado."}
