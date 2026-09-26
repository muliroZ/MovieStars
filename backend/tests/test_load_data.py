import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, text

from app.db.base import Base
from app.movies import models  # noqa: F401  Registra os modelos ORM.
from app.movies.load_data import (
    CSV_FILES,
    DEFAULT_DATA_DIR,
    LoadError,
    LoadReport,
    TableStats,
    check_files,
    check_tables,
    convert_value,
    fix_synopsis_quotes,
    load_file,
    read_existing_keys,
)

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


# --- T-03: check_files (CA-14) ---


def test_check_files_accepts_valid_csvs(csv_dir: Path) -> None:
    check_files(csv_dir)


def test_check_files_reports_missing_file(csv_dir: Path) -> None:
    (csv_dir / "bases_atv_dev1/dim_genres.csv").unlink()

    with pytest.raises(LoadError, match="dim_genres.csv: arquivo não encontrado"):
        check_files(csv_dir)


def test_check_files_reports_missing_columns(csv_dir: Path) -> None:
    write_csv(
        csv_dir / "bases_atv_dev_2/movies_reviews.csv",
        ["sk_movie_review_id", "sk_movie_id", "nome"],
        [["rv1", "m1", "Ana"]],
    )

    with pytest.raises(LoadError, match="movies_reviews.csv não tem as colunas: nota, comentario"):
        check_files(csv_dir)


def test_check_files_reports_every_problem_at_once(csv_dir: Path) -> None:
    (csv_dir / "bases_atv_dev1/dim_genres.csv").unlink()
    write_csv(csv_dir / "bases_atv_dev1/dim_people.csv", ["nome_pessoa"], [["Ana"]])

    with pytest.raises(LoadError) as error:
        check_files(csv_dir)

    message = str(error.value)
    assert "dim_genres.csv" in message
    assert "dim_people.csv não tem as colunas: sk_person_id, tipo_pessoa" in message


def test_check_files_ignores_extra_columns(csv_dir: Path) -> None:
    header, rows = VALID_CSVS["bases_atv_dev1/dim_genres.csv"]
    write_csv(
        csv_dir / "bases_atv_dev1/dim_genres.csv",
        [*header, "coluna_extra"],
        [[*row, "x"] for row in rows],
    )

    check_files(csv_dir)


# --- T-04: check_tables (CA-3) ---


def test_check_tables_accepts_migrated_database(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        check_tables(conn)
    engine.dispose()


def test_check_tables_asks_for_migrations_when_tables_are_missing(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'vazio.db'}")
    with engine.connect() as conn, pytest.raises(LoadError, match="alembic upgrade head"):
        check_tables(conn)
    engine.dispose()


# --- T-05: convert_value (CA-7, CA-8, CA-9, CA-13) ---


def column(table: str, name: str):
    return Base.metadata.tables[table].c[name]


@pytest.mark.parametrize(
    ("table", "name", "raw", "expected"),
    [
        ("dim_movies", "titulo", " Ação & Reação ", " Ação & Reação "),
        ("dim_movies", "ano_lancamento", "2017", 2017),
        ("fact_movies_performance", "qtd_tmdb", "2375.0", 2375),
        ("fact_movies_performance", "nota_tmdb", "4.966", 4.966),
        ("movie_reviews", "nota", "9.8", 9.8),
        ("fact_movies_performance", "lucro_brl", "-32363250.0", Decimal("-32363250.0")),
        ("dim_movies", "data_lancamento", "2017-02-01", date(2017, 2, 1)),
    ],
)
def test_convert_value_valid(table: str, name: str, raw: str, expected: object) -> None:
    assert convert_value(column(table, name), raw) == expected


@pytest.mark.parametrize(
    ("table", "name"),
    [
        ("dim_movies", "titulo"),
        ("dim_movies", "duracao_minutos"),
        ("fact_movies_performance", "popularidade"),
        ("fact_movies_performance", "orcamento_usd"),
        ("dim_movies", "data_lancamento"),
    ],
)
def test_convert_value_empty_is_none(table: str, name: str) -> None:
    assert convert_value(column(table, name), "") is None


@pytest.mark.parametrize(
    ("table", "name", "raw"),
    [
        ("dim_movies", "duracao_minutos", "abc"),
        ("fact_movies_performance", "qtd_tmdb", "2375.5"),
        ("fact_movies_performance", "nota_tmdb", "alta"),
        ("fact_movies_performance", "nota_tmdb", "nan"),
        ("fact_movies_performance", "orcamento_usd", "1.000,00"),
        ("dim_movies", "data_lancamento", "01/02/2017"),
        ("dim_movies", "data_lancamento", "2017-02-30"),
    ],
)
def test_convert_value_invalid_raises(table: str, name: str, raw: str) -> None:
    with pytest.raises(ValueError):
        convert_value(column(table, name), raw)


# --- T-06: fix_synopsis_quotes (CA-18) ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # aspas nas duas pontas
        ('"Julia vê um ""filme"" raro."', 'Julia vê um "filme" raro.'),
        # só a inicial: texto cortado na origem
        ('"Due to ""The Shift"" 50% of', 'Due to "The Shift" 50% of'),
        # cortado logo após uma aspa interna: termina em ""
        ('"Known as ""Treasure Day""', 'Known as "Treasure Day"'),
        # citação no fim do texto, com fechamento: termina em """
        ('"He watched ""Grizzly"""', 'He watched "Grizzly"'),
        # aspas legítimas no início do texto original
        ('"""Kill Bill"" é citado."', '"Kill Bill" é citado.'),
    ],
)
def test_fix_synopsis_quotes_corrects_escaped_text(raw: str, expected: str) -> None:
    assert fix_synopsis_quotes(raw) == (expected, True)


@pytest.mark.parametrize(
    "raw",
    ["Sinopse comum.", "Oberon, conhecido como 'OZ\"", 'Ele disse "oi" e saiu.', ""],
)
def test_fix_synopsis_quotes_keeps_other_text(raw: str) -> None:
    assert fix_synopsis_quotes(raw) == (raw, False)


# --- Apoio aos testes de gravação ---

MOVIES = "bases_atv_dev1/dim_movies.csv"
GENRES = "bases_atv_dev1/dim_genres.csv"
PEOPLE = "bases_atv_dev1/dim_people.csv"
BRIDGE_GENRE = "bases_atv_dev_2/bridge_movie_genre.csv"
BRIDGE_PERSON = "bases_atv_dev_2/bridge_movie_person.csv"
DIM_REVIEWS = "bases_atv_dev1/dim_reviews.csv"
REVIEWS = "bases_atv_dev_2/movies_reviews.csv"
PARENT_TABLES = {"dim_movies", "dim_genres", "dim_companies", "dim_people"}


def engine_with_foreign_keys(database_url: str) -> Engine:
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


def load_tables(database_url: str, csv_dir: Path, tables: set[str] | None = None) -> LoadReport:
    """Roda `load_file` para as tabelas pedidas (todas, se None), numa transação."""

    engine = engine_with_foreign_keys(database_url)
    report = LoadReport()
    with engine.begin() as conn:
        known = read_existing_keys(conn)
        for csv_file in CSV_FILES:
            if tables is None or csv_file.table in tables:
                load_file(conn, csv_dir, csv_file, known, report)
    engine.dispose()
    return report


def fetch(database_url: str, sql: str) -> list[tuple]:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = [tuple(row) for row in conn.execute(text(sql))]
    engine.dispose()
    return rows


def write_rows(csv_dir: Path, relative_path: str, rows: list[list[str]]) -> None:
    """Reescreve um CSV do conjunto válido com outras linhas (mesmo cabeçalho)."""

    header, _ = VALID_CSVS[relative_path]
    write_csv(csv_dir / relative_path, header, rows)


def stats_of(report: LoadReport, table: str) -> TableStats:
    return next(stats for stats in report.tables if stats.table == table)


# --- T-07: read_existing_keys (CA-6, CA-10) ---


def test_read_existing_keys_on_empty_database(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        known = read_existing_keys(conn)
    engine.dispose()

    assert all(keys == set() for keys in known.keys.values())
    assert all(values == {} for values in known.unique.values())


def test_read_existing_keys_returns_saved_rows(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO dim_genres VALUES ('g1', 'Drama')"))
        conn.execute(text("INSERT INTO dim_people VALUES ('p1', 'Alice Braga', 'Ator')"))
    with engine.connect() as conn:
        known = read_existing_keys(conn)
    engine.dispose()

    assert known.keys["dim_genres"] == {"g1"}
    assert known.unique["dim_genres"] == {("Drama",): ("g1",)}
    assert known.unique["dim_people"] == {("Alice Braga", "Ator"): ("p1",)}
    assert known.keys["dim_movies"] == set()


# --- T-08: load_file nas tabelas pai (CA-5, CA-7, CA-12, CA-13, CA-17, CA-18) ---


def test_load_parents_saves_valid_rows(database_url: str, csv_dir: Path) -> None:
    report = load_tables(database_url, csv_dir, PARENT_TABLES)

    movies = stats_of(report, "dim_movies")
    assert (movies.read, movies.inserted, movies.ignored, movies.discarded) == (3, 3, 0, 0)
    assert stats_of(report, "dim_people").inserted == 3
    assert report.issues == {}
    assert report.synopses_fixed == 1

    rows = fetch(
        database_url,
        "SELECT sk_movie_id, titulo, data_lancamento, duracao_minutos, status_filme, sinopse,"
        " url_poster FROM dim_movies ORDER BY sk_movie_id",
    )
    assert rows[1][5] == 'Julia fica "preocupada" com Holt.'
    # células vazias viram NULL; duração 0 fica como está (D-2)
    assert rows[2] == ("m3", "Filme Futuro", None, 0, "Planejado", None, None)
    assert rows[0][4] == "Lançado"
    assert fetch(database_url, "SELECT nome_pessoa FROM dim_people WHERE sk_person_id = 'p3'") == [
        ("F. Javier Gutiérrez",)
    ]


def test_load_parents_discards_invalid_rows(database_url: str, csv_dir: Path) -> None:
    header, valid_rows = VALID_CSVS[MOVIES]
    m1 = valid_rows[0]
    write_rows(
        csv_dir,
        MOVIES,
        [
            m1,  # linha 2
            ["m4", "104", "", "", "", "", "", "", "", ""],  # 3: título vazio
            m1,  # 4: chave repetida
            ["m5", "101", "Outro", "", "", "", "", "", "", ""],  # 5: id_filme repetido
            [*m1[:1], "106", *m1[2:], "extra"],  # 6: coluna a mais
        ],
    )
    write_rows(csv_dir, GENRES, [["Drama", "g1"], ["Drama", "g9"]])
    write_rows(csv_dir, PEOPLE, [["Ana", "Ator", "p1"], ["Beto", "Produtor", "p2"]])

    report = load_tables(database_url, csv_dir, PARENT_TABLES)

    assert stats_of(report, "dim_movies").inserted == 1
    assert stats_of(report, "dim_movies").discarded == 4
    assert report.issues == {
        ("dim_movies.csv", "linha descartada: titulo vazio"): [3],
        ("dim_movies.csv", "linha descartada: chave repetida no arquivo"): [4],
        ("dim_movies.csv", "linha descartada: id_filme já usado por outra chave"): [5],
        ("dim_movies.csv", "linha descartada: número de colunas diferente do cabeçalho"): [6],
        ("dim_genres.csv", "linha descartada: nome_genero já usado por outra chave"): [3],
        (
            "dim_people.csv",
            "linha descartada: tipo_pessoa diferente de Ator, Diretor ou Roteirista",
        ): [3],
    }
    assert fetch(database_url, "SELECT sk_genre_id FROM dim_genres") == [("g1",)]


def test_invalid_optional_value_is_nulled(database_url: str, csv_dir: Path) -> None:
    write_rows(
        csv_dir,
        MOVIES,
        [["m1", "101", "Rings", "01/02/2017", "2017", "abc", "", "", "", ""]],
    )

    report = load_tables(database_url, csv_dir, {"dim_movies"})

    assert stats_of(report, "dim_movies").inserted == 1
    assert report.issues == {
        ("dim_movies.csv", "campo anulado: data_lancamento inválido"): [2],
        ("dim_movies.csv", "campo anulado: duracao_minutos inválido"): [2],
    }
    assert fetch(database_url, "SELECT data_lancamento, duracao_minutos FROM dim_movies") == [
        (None, None)
    ]


# --- T-09: load_file nas tabelas filhas (CA-6, CA-9, CA-12) ---


def test_load_all_files_saves_children(database_url: str, csv_dir: Path) -> None:
    report = load_tables(database_url, csv_dir)

    inserted = {stats.table: stats.inserted for stats in report.tables}
    assert inserted == {
        "dim_movies": 3,
        "dim_genres": 2,
        "dim_companies": 2,
        "dim_people": 3,
        "bridge_movie_genre": 3,
        "bridge_movie_company": 2,
        "bridge_movie_person": 3,
        "fact_movies_performance": 2,
        "dim_reviews": 2,
        "movie_reviews": 3,
    }
    assert report.issues == {}
    # notas gravadas na escala 0–10, sem conversão (CA-9)
    assert fetch(
        database_url, "SELECT nota FROM movie_reviews WHERE sk_movie_review_id = 'rv1'"
    ) == [(9.8,)]
    assert fetch(
        database_url,
        "SELECT qtd_tmdb, orcamento_usd FROM fact_movies_performance ORDER BY sk_movie_id",
    ) == [(7500, 3300000), (None, None)]
    assert fetch(
        database_url, "SELECT nota_media_usuarios FROM dim_reviews WHERE sk_movie_id = 'm2'"
    ) == [(None,)]


def test_children_of_missing_or_discarded_parents_are_discarded(
    database_url: str, csv_dir: Path
) -> None:
    write_rows(csv_dir, GENRES, [["Drama", "g1"], ["Drama", "g2"]])  # g2 é descartado
    write_rows(csv_dir, BRIDGE_GENRE, [["m1", "g1"], ["m2", "g2"], ["m9", "g1"]])

    report = load_tables(database_url, csv_dir)

    assert stats_of(report, "bridge_movie_genre").inserted == 1
    assert report.issues[
        ("bridge_movie_genre.csv", "linha descartada: gênero inexistente ou descartado")
    ] == [3]
    assert report.issues[
        ("bridge_movie_genre.csv", "linha descartada: filme inexistente ou descartado")
    ] == [4]


def test_invalid_children_rows_are_discarded(database_url: str, csv_dir: Path) -> None:
    write_rows(
        csv_dir,
        REVIEWS,
        [
            ["rv1", "m1", "Ana", "9.8", "Muito bom."],
            ["rv2", "m1", "Beto", "11", "Nota alta demais."],
            ["rv3", "m1", "Caio", "-1", "Nota negativa."],
            ["rv4", "m1", "Duda", "7.0", ""],
        ],
    )
    write_rows(csv_dir, BRIDGE_PERSON, [["m1", "p1"], ["m1", "p1"]])
    write_rows(csv_dir, DIM_REVIEWS, [["m1", "m1", "2", "9.0"], ["x9", "m1", "1", "5.0"]])

    report = load_tables(database_url, csv_dir)

    assert stats_of(report, "movie_reviews").inserted == 1
    assert report.issues[("movies_reviews.csv", "linha descartada: nota fora de 0–10")] == [3, 4]
    assert report.issues[("movies_reviews.csv", "linha descartada: comentario vazio")] == [5]
    assert report.issues[
        ("bridge_movie_person.csv", "linha descartada: chave repetida no arquivo")
    ] == [3]
    assert report.issues[
        ("dim_reviews.csv", "linha descartada: sk_movie_id já usado por outra chave")
    ] == [3]
