import csv
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from app.movies import models  # noqa: F401  Registra os modelos ORM.
from app.movies.load_data import CSV_FILES, DEFAULT_DATA_DIR

# CSVs mínimos e válidos: {caminho relativo: (cabeçalho, linhas)}.
VALID_CSVS: dict[str, tuple[list[str], list[list[str]]]] = {
    "bases_atv_dev1/dim_movies.csv": (
        [
            "sk_movie_id",
            "id_filme",
            "titulo",
            "data_lancamento",
            "ano_lancamento",
            "duracao_minutos",
            "status_filme",
            "sinopse",
            "url_poster",
            "url_backdrop",
        ],
        [
            [
                "m1",
                "101",
                "Cidade de Deus",
                "2002-08-30",
                "2002",
                "130",
                "Lançado",
                "Buscapé cresce em meio à violência.",
                "https://image.tmdb.org/t/p/w500/p1.jpg",
                "",
            ],
            [
                "m2",
                "102",
                "Rings",
                "2017-02-01",
                "2017",
                "102",
                "Lançado",
                '"Julia fica ""preocupada"" com Holt."',
                "",
                "",
            ],
            ["m3", "103", "Filme Futuro", "", "", "0", "Planejado", "", "", ""],
        ],
    ),
    "bases_atv_dev1/dim_genres.csv": (
        ["nome_genero", "sk_genre_id"],
        [["Drama", "g1"], ["Horror", "g2"]],
    ),
    "bases_atv_dev1/dim_companies.csv": (
        ["nome_produtora", "sk_company_id"],
        [["O2 Filmes", "c1"], ["Universal Pictures", "c2"]],
    ),
    "bases_atv_dev1/dim_people.csv": (
        ["nome_pessoa", "tipo_pessoa", "sk_person_id"],
        [
            ["Fernando Meirelles", "Diretor", "p1"],
            ["Alice Braga", "Ator", "p2"],
            ["F. Javier Gutiérrez", "Diretor", "p3"],
        ],
    ),
    "bases_atv_dev_2/bridge_movie_genre.csv": (
        ["sk_movie_id", "sk_genre_id"],
        [["m1", "g1"], ["m2", "g2"], ["m3", "g1"]],
    ),
    "bases_atv_dev_2/bridge_movie_company.csv": (
        ["sk_movie_id", "sk_company_id"],
        [["m1", "c1"], ["m2", "c2"]],
    ),
    "bases_atv_dev_2/bridge_movie_person.csv": (
        ["sk_movie_id", "sk_person_id"],
        [["m1", "p1"], ["m1", "p2"], ["m2", "p3"]],
    ),
    "bases_atv_dev_2/fact_movies_performance.csv": (
        [
            "sk_movie_id",
            "orcamento_usd",
            "receita_usd",
            "lucro_usd",
            "orcamento_brl",
            "receita_brl",
            "lucro_brl",
            "popularidade",
            "nota_tmdb",
            "qtd_tmdb",
            "nota_imdb",
            "qtd_imdb",
        ],
        [
            [
                "m1",
                "3300000.0",
                "30641770.0",
                "27341770.0",
                "10385100.0",
                "96429950.19",
                "86044850.19",
                "15.2",
                "8.4",
                "7500.0",
                "8.6",
                "780000.0",
            ],
            ["m3", "", "", "0.0", "", "", "0.0", "", "0.0", "", "", ""],
        ],
    ),
    "bases_atv_dev1/dim_reviews.csv": (
        ["sk_review_id", "sk_movie_id", "qtd_avaliacoes_usuarios", "nota_media_usuarios"],
        [["m1", "m1", "2", "9.0"], ["m2", "m2", "0", ""]],
    ),
    "bases_atv_dev_2/movies_reviews.csv": (
        ["sk_movie_review_id", "sk_movie_id", "nome", "nota", "comentario"],
        [
            ["rv1", "m1", "Henrique Carvalho", "9.8", "Adorei cada minuto, inesquecível."],
            ["rv2", "m1", "Lucas Silva", "8.2", "Ótimo entretenimento."],
            ["rv3", "m2", "Gabriela Cardoso", "2.4", "Horrível! Perda de tempo."],
        ],
    ),
}


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Escreve um CSV; `movies_reviews.csv` usa CRLF, como o arquivo real."""

    path.parent.mkdir(parents=True, exist_ok=True)
    line_end = "\r\n" if path.name == "movies_reviews.csv" else "\n"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator=line_end)
        writer.writerow(header)
        writer.writerows(rows)


@pytest.fixture
def csv_dir(tmp_path: Path) -> Path:
    """Pasta temporária com os dez CSVs mínimos válidos."""

    data_dir = tmp_path / "data"
    for relative_path, (header, rows) in VALID_CSVS.items():
        write_csv(data_dir / relative_path, header, rows)
    return data_dir


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    """Banco SQLite temporário já com o esquema da aplicação."""

    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


def test_csv_files_cover_all_tables() -> None:
    assert {csv_file.table for csv_file in CSV_FILES} == set(Base.metadata.tables)
    assert len(CSV_FILES) == len(Base.metadata.tables)


def test_default_data_dir_points_to_repository_data() -> None:
    assert DEFAULT_DATA_DIR.name == "data"
    assert (DEFAULT_DATA_DIR / CSV_FILES[0].path).is_file()


def test_fixtures_write_every_csv(csv_dir: Path, database_url: str) -> None:
    assert {csv_file.path for csv_file in CSV_FILES} == set(VALID_CSVS)
    for csv_file in CSV_FILES:
        assert (csv_dir / csv_file.path).is_file()
    assert database_url.startswith("sqlite:///")
