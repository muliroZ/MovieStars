from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import (
    DimCompany,
    DimGenre,
    DimMovie,
    DimPerson,
    DimReview,
    FactMoviePerformance,
)
from app.movies.schemas import MovieInput
from tests.helpers import add_movie

# --- T-03: mensagens de validação em português (CA-14) ---


async def test_validation_errors_are_in_portuguese(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies", params={"page": 0, "page_size": "abc"})

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "page"],
                "msg": "Deve ser no mínimo 1.",
                "type": "greater_than_equal",
            },
            {
                "loc": ["query", "page_size"],
                "msg": "Deve ser um número inteiro.",
                "type": "int_parsing",
            },
        ]
    }


async def test_search_too_long_message(client: AsyncClient) -> None:
    response = await client.get("/api/v1/movies", params={"search": "x" * 201})

    assert response.json()["detail"][0]["msg"] == "Deve ter no máximo 200 caracteres."


# --- T-04: GET /genres e GET /directors (CA-2, CA-13, CA-16) ---


async def add_people(session: AsyncSession, *people: tuple[str, str]) -> None:
    session.add_all(DimPerson(nome_pessoa=name, tipo_pessoa=tipo) for name, tipo in people)
    await session.commit()


async def test_genres_in_alphabetical_order(client: AsyncClient, session: AsyncSession) -> None:
    session.add_all(DimGenre(nome_genero=name) for name in ["Western", "Action", "Drama"])
    await session.commit()

    response = await client.get("/api/v1/genres")

    assert response.status_code == 200
    assert response.json() == ["Action", "Drama", "Western"]


async def test_directors_ignore_accents_and_only_directors(
    client: AsyncClient, session: AsyncSession
) -> None:
    await add_people(
        session,
        ("Alberto Rodríguez", "Diretor"),
        ("Alberto Rodriguez", "Diretor"),
        ("Rodrigo Aragão", "Diretor"),
        ("Rodrigo Ator", "Ator"),
        ("Fernando Meirelles", "Diretor"),
    )

    response = await client.get("/api/v1/directors", params={"search": "RODRÍ"})

    assert response.status_code == 200
    # começam com o termo primeiro, depois os que só contêm
    assert response.json() == ["Rodrigo Aragão", "Alberto Rodriguez", "Alberto Rodríguez"]


async def test_directors_exact_name_first_and_limit(
    client: AsyncClient, session: AsyncSession
) -> None:
    await add_people(session, *((f"Ana {letter}", "Diretor") for letter in "ABCDEFGHIJKL"))
    await add_people(session, ("Zé Ana", "Diretor"))

    response = await client.get("/api/v1/directors", params={"search": "Zé Ana"})
    many = await client.get("/api/v1/directors", params={"search": "ana"})

    assert response.json()[0] == "Zé Ana"
    assert len(many.json()) == 10
    assert many.json()[:2] == ["Ana A", "Ana B"]


async def test_directors_treat_percent_as_text(client: AsyncClient, session: AsyncSession) -> None:
    await add_people(session, ("Diretor 100%", "Diretor"), ("Diretor 1000", "Diretor"))

    response = await client.get("/api/v1/directors", params={"search": "100%"})

    assert response.json() == ["Diretor 100%"]


@pytest.mark.parametrize("params", [{}, {"search": "a"}, {"search": "x" * 256}])
async def test_directors_validate_search(client: AsyncClient, params: dict) -> None:
    response = await client.get("/api/v1/directors", params=params)

    assert response.status_code == 422


# --- T-05: MovieInput (CA-6 a CA-12, CA-18, CA-19) ---

VALID = {"titulo": "Cidade de Deus", "ano_lancamento": 2002, "status_filme": "Lançado"}
MAX_YEAR = date.today().year + 10


def errors_of(data: dict) -> dict[str, str]:
    """Campo → mensagem dos erros de validação do schema."""

    with pytest.raises(ValidationError) as error:
        MovieInput.model_validate({**VALID, **data})
    return {
        str(item["loc"][0]): str(item["msg"]).removeprefix("Value error, ")
        for item in error.value.errors()
    }


def test_movie_input_minimal_and_cleanup() -> None:
    movie = MovieInput.model_validate(
        {
            **VALID,
            "titulo": "  Cidade de Deus  ",
            "sinopse": "   ",
            "url_poster": "",
            "generos": ["Drama", "Crime", "Drama"],
            "diretores": [" Kátia Lund ", "Kátia Lund", "Fernando Meirelles"],
        }
    )

    assert movie.titulo == "Cidade de Deus"
    assert (movie.sinopse, movie.url_poster, movie.data_lancamento) == (None, None, None)
    assert movie.generos == ["Drama", "Crime"]
    assert movie.diretores == ["Kátia Lund", "Fernando Meirelles"]


def test_movie_input_accepts_limits() -> None:
    movie = MovieInput.model_validate(
        {
            **VALID,
            "titulo": "x" * 500,
            "ano_lancamento": MAX_YEAR,
            "data_lancamento": f"{MAX_YEAR}-12-31",
            "duracao_minutos": 1000,
            "sinopse": "s" * 4000,
            "url_poster": "http://exemplo.com/p.jpg",
            "url_backdrop": "https://exemplo.com/b.jpg",
            "diretores": ["d" * 255],
        }
    )

    assert movie.duracao_minutos == 1000


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"titulo": "   "}, "titulo"),
        ({"titulo": "x" * 501}, "titulo"),
        ({"ano_lancamento": 1887}, "ano_lancamento"),
        ({"ano_lancamento": MAX_YEAR + 1}, "ano_lancamento"),
        ({"status_filme": "Cancelado"}, "status_filme"),
        ({"data_lancamento": "2017-02-30"}, "data_lancamento"),
        ({"duracao_minutos": 0}, "duracao_minutos"),
        ({"duracao_minutos": 1001}, "duracao_minutos"),
        ({"sinopse": "s" * 4001}, "sinopse"),
        ({"url_poster": "x" * 2049}, "url_poster"),
        ({"diretores": ["d" * 256]}, "diretores"),
        ({"diretores": ["   "]}, "diretores"),
    ],
)
def test_movie_input_rejects_invalid(data: dict, field: str) -> None:
    assert field in errors_of(data)


def test_movie_input_custom_messages() -> None:
    assert errors_of({"data_lancamento": "2017-02-01", "ano_lancamento": 2018}) == {
        "ano_lancamento": "O ano deve ser o mesmo da data de lançamento."
    }
    assert errors_of({"url_backdrop": "www.exemplo.com"}) == {
        "url_backdrop": "Deve começar com http:// ou https://."
    }
    assert errors_of({"ano_lancamento": 1887}) == {
        "ano_lancamento": f"Deve estar entre 1888 e {MAX_YEAR}."
    }


# --- T-06: POST /api/v1/movies (CA-3 a CA-5, CA-13, CA-14, CA-17, CA-18) ---

FULL_MOVIE = {
    "titulo": "  Cidade de Deus  ",
    "ano_lancamento": 2002,
    "status_filme": "Lançado",
    "data_lancamento": "2002-08-30",
    "duracao_minutos": 130,
    "sinopse": "Buscapé cresce em meio à violência.",
    "url_poster": "https://exemplo.com/p.jpg",
    "url_backdrop": "",
    "generos": ["Drama", "Crime"],
    "diretores": ["Fernando Meirelles", "Kátia Lund"],
}


async def count_directors(session: AsyncSession, name: str) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(DimPerson)
        .where(DimPerson.nome_pessoa == name, DimPerson.tipo_pessoa == "Diretor")
    )


async def test_post_movie_creates_full_movie(client: AsyncClient, session: AsyncSession) -> None:
    session.add_all([DimGenre(nome_genero="Crime"), DimGenre(nome_genero="Drama")])
    await add_people(session, ("Fernando Meirelles", "Diretor"), ("Kátia Lund", "Ator"))

    response = await client.post("/api/v1/movies", json=FULL_MOVIE)

    assert response.status_code == 201
    body = response.json()
    assert body["titulo"] == "Cidade de Deus"
    assert (body["data_lancamento"], body["duracao_minutos"], body["status_filme"]) == (
        "2002-08-30",
        130,
        "Lançado",
    )
    assert body["url_backdrop"] is None
    assert body["generos"] == ["Crime", "Drama"]
    assert body["diretores"] == ["Fernando Meirelles", "Kátia Lund"]
    id_filme = await session.scalar(
        select(DimMovie.id_filme).where(DimMovie.sk_movie_id == body["sk_movie_id"])
    )
    assert UUID(id_filme).version == 4
    # diretor existente reaproveitado; "Kátia Lund" só existia como Ator → diretor novo
    assert await count_directors(session, "Fernando Meirelles") == 1
    assert await count_directors(session, "Kátia Lund") == 1
    found = (await client.get("/api/v1/movies", params={"search": "cidade de deus"})).json()
    assert [item["sk_movie_id"] for item in found["items"]] == [body["sk_movie_id"]]


async def test_post_minimal_movie(client: AsyncClient) -> None:
    response = await client.post("/api/v1/movies", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert (body["media_estrelas"], body["qtd_avaliacoes"], body["financeiro"]) == (None, 0, None)
    assert body["generos"] == body["diretores"] == body["roteiristas"] == []
    assert body["elenco"] == body["produtoras"] == []
    assert body["data_lancamento"] is None


async def test_post_movie_creates_director_with_different_accent(
    client: AsyncClient, session: AsyncSession
) -> None:
    await add_people(session, ("Alberto Rodríguez", "Diretor"))

    response = await client.post(
        "/api/v1/movies", json={**VALID, "diretores": ["Alberto Rodriguez"]}
    )

    assert response.json()["diretores"] == ["Alberto Rodriguez"]
    assert await count_directors(session, "Alberto Rodríguez") == 1
    assert await count_directors(session, "Alberto Rodriguez") == 1


async def test_post_movie_rejects_unknown_genre(client: AsyncClient, session: AsyncSession) -> None:
    session.add(DimGenre(nome_genero="Drama"))
    await session.commit()

    response = await client.post("/api/v1/movies", json={**VALID, "generos": ["Drama", "Terror"]})

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "generos"],
                "msg": "Gênero inexistente: Terror.",
                "type": "value_error",
            }
        ]
    }
    assert await session.scalar(select(func.count()).select_from(DimMovie)) == 0


async def test_post_movie_field_errors_in_portuguese(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/movies",
        json={
            "titulo": "   ",
            "data_lancamento": "2017-02-01",
            "ano_lancamento": 2018,
            "status_filme": "Cancelado",
            "duracao_minutos": 0,
            "url_poster": "ftp://exemplo.com",
        },
    )

    assert response.status_code == 422
    messages = {tuple(error["loc"]): error["msg"] for error in response.json()["detail"]}
    assert messages == {
        ("body", "titulo"): "Campo obrigatório.",
        ("body", "ano_lancamento"): "O ano deve ser o mesmo da data de lançamento.",
        ("body", "status_filme"): "Valor inválido.",
        ("body", "duracao_minutos"): "Deve ser no mínimo 1.",
        ("body", "url_poster"): "Deve começar com http:// ou https://.",
    }


async def test_post_movie_requires_title_year_and_status(client: AsyncClient) -> None:
    response = await client.post("/api/v1/movies", json={})

    messages = {error["loc"][1]: error["msg"] for error in response.json()["detail"]}
    assert messages == {
        "titulo": "Campo obrigatório.",
        "ano_lancamento": "Campo obrigatório.",
        "status_filme": "Campo obrigatório.",
    }


# --- T-07: PUT /api/v1/movies/{sk_movie_id} (CA-21 a CA-23, CA-25) ---


async def movie_with_everything(session: AsyncSession) -> DimMovie:
    return await add_movie(
        session,
        "Título Antigo",
        2017,
        duracao_minutos=0,
        genres=[DimGenre(nome_genero="Horror"), DimGenre(nome_genero="Drama")],
        people=[
            DimPerson(nome_pessoa="Diretora Mantida", tipo_pessoa="Diretor"),
            DimPerson(nome_pessoa="Diretor Retirado", tipo_pessoa="Diretor"),
            DimPerson(nome_pessoa="Roteirista Um", tipo_pessoa="Roteirista"),
            DimPerson(nome_pessoa="Atriz Um", tipo_pessoa="Ator"),
        ],
        companies=[DimCompany(nome_produtora="Produtora Um")],
        performance=FactMoviePerformance(
            orcamento_usd=Decimal("10"),
            receita_usd=Decimal("30"),
            lucro_usd=Decimal("20"),
            lucro_brl=Decimal("0"),
        ),
        notas=[8.0, 6.0],
    )


async def test_put_movie_updates_editable_fields_only(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await movie_with_everything(session)
    payload = {
        "titulo": "Título Novo Ação",
        "ano_lancamento": 2018,
        "status_filme": "Planejado",
        "data_lancamento": "2018-05-01",
        "duracao_minutos": 95,
        "sinopse": "Nova sinopse.",
        "generos": ["Drama"],
        "diretores": ["Diretora Mantida", "Diretor Novo"],
    }

    response = await client.put(f"/api/v1/movies/{movie.sk_movie_id}", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert (body["titulo"], body["ano_lancamento"], body["status_filme"]) == (
        "Título Novo Ação",
        2018,
        "Planejado",
    )
    assert (body["duracao_minutos"], body["sinopse"], body["url_poster"]) == (
        95,
        "Nova sinopse.",
        None,
    )
    assert body["generos"] == ["Drama"]
    assert body["diretores"] == ["Diretor Novo", "Diretora Mantida"]
    # o que o formulário não edita continua igual (CA-22)
    assert (body["roteiristas"], body["elenco"], body["produtoras"]) == (
        ["Roteirista Um"],
        ["Atriz Um"],
        ["Produtora Um"],
    )
    assert body["financeiro"]["lucro_usd"] == 20.0
    assert (body["media_estrelas"], body["qtd_avaliacoes"]) == (3.5, 2)


async def test_put_movie_updates_search_and_order(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await movie_with_everything(session)

    await client.put(
        f"/api/v1/movies/{movie.sk_movie_id}", json={**VALID, "titulo": "Ação Renomeada"}
    )

    new_title = (await client.get("/api/v1/movies", params={"search": "acao renomeada"})).json()
    old_title = (await client.get("/api/v1/movies", params={"search": "título antigo"})).json()
    assert [item["sk_movie_id"] for item in new_title["items"]] == [movie.sk_movie_id]
    assert old_title["total"] == 0


async def test_put_movie_keeps_removed_director_registered(
    client: AsyncClient, session: AsyncSession
) -> None:
    movie = await movie_with_everything(session)

    await client.put(f"/api/v1/movies/{movie.sk_movie_id}", json={**VALID, "diretores": []})

    assert await count_directors(session, "Diretor Retirado") == 1
    suggestions = await client.get("/api/v1/directors", params={"search": "retirado"})
    assert suggestions.json() == ["Diretor Retirado"]


async def test_put_unknown_movie_returns_404(client: AsyncClient) -> None:
    response = await client.put("/api/v1/movies/nao-existe", json=VALID)

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado."}


async def test_put_movie_rejects_invalid_body(client: AsyncClient, session: AsyncSession) -> None:
    movie = await movie_with_everything(session)

    response = await client.put(
        f"/api/v1/movies/{movie.sk_movie_id}", json={**VALID, "ano_lancamento": 1800}
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "ano_lancamento"]


# --- T-08: DELETE /api/v1/movies/{sk_movie_id} (CA-27 a CA-29) ---


async def count(session: AsyncSession, table: str) -> int:
    return await session.scalar(text(f"SELECT COUNT(*) FROM {table}"))


async def test_delete_movie_cascades_dependents(client: AsyncClient, session: AsyncSession) -> None:
    movie = await movie_with_everything(session)
    session.add(DimReview(sk_movie_id=movie.sk_movie_id, qtd_avaliacoes_usuarios=2))
    await session.commit()
    kept = await add_movie(session, "Outro Filme", notas=[5.0])

    response = await client.delete(f"/api/v1/movies/{movie.sk_movie_id}")

    assert response.status_code == 204
    assert response.content == b""
    dependents = [
        "movie_reviews",
        "bridge_movie_genre",
        "bridge_movie_person",
        "bridge_movie_company",
        "fact_movies_performance",
        "dim_reviews",
    ]
    counts = {table: await count(session, table) for table in dependents}
    # só a avaliação do outro filme continua
    assert counts == {table: 1 if table == "movie_reviews" else 0 for table in dependents}
    assert (await count(session, "dim_genres"), await count(session, "dim_companies")) == (2, 1)
    assert await count(session, "dim_people") == 4
    assert (await client.get(f"/api/v1/movies/{movie.sk_movie_id}")).status_code == 404
    assert (await client.get(f"/api/v1/movies/{kept.sk_movie_id}")).status_code == 200


async def test_delete_unknown_movie_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/movies/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Filme não encontrado."}
