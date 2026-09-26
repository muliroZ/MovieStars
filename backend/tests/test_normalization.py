import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.movies.models import DimMovie
from app.movies.normalization import normalize_title


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("À La Recherche", "a la recherche"),
        ("AÇÃO", "acao"),
        ("ação", "acao"),
        ("Straße", "strasse"),
        ("Polícia Federal: A Lei É Para Todos", "policia federal: a lei e para todos"),
    ],
)
def test_normalize_title_removes_accents_and_case(text: str, expected: str) -> None:
    assert normalize_title(text) == expected


@pytest.mark.parametrize(
    "text",
    ['"""blessed"""', " rings", "100% lobo", "07/27/1978", "君の名は", ""],
)
def test_normalize_title_keeps_other_characters(text: str) -> None:
    assert normalize_title(text) == text


def test_orm_insert_fills_titulo_normalizado() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(DimMovie(sk_movie_id="m1", id_filme="1", titulo="À La Recherche"))
        session.commit()

        assert session.get(DimMovie, "m1").titulo_normalizado == "a la recherche"
    engine.dispose()
