"""Carga inicial do catálogo a partir dos CSVs da pasta `data/`.

Uso (de dentro de `backend/`):

    .venv/bin/python -m app.movies.load_data [--data-dir PASTA] [--reset]

A carga roda em uma única transação: ou todos os arquivos são gravados, ou
nada é gravado. Ver `specs/features/000-carga-de-dados/`.
"""

import csv
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import (
    Column,
    Connection,
    Date,
    Float,
    Integer,
    Numeric,
    String,
    Table,
    func,
    inspect,
    select,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.base import Base
from app.movies import models  # também registra as tabelas no metadata

# load_data.py → movies → app → backend → raiz do repositório.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class CsvFile:
    """Um arquivo CSV e a tabela que ele alimenta."""

    path: str  # relativo à pasta de dados
    table: str


# Ordem de carga: tabelas pai antes das tabelas que apontam para elas.
CSV_FILES: tuple[CsvFile, ...] = (
    CsvFile("bases_atv_dev1/dim_movies.csv", "dim_movies"),
    CsvFile("bases_atv_dev1/dim_genres.csv", "dim_genres"),
    CsvFile("bases_atv_dev1/dim_companies.csv", "dim_companies"),
    CsvFile("bases_atv_dev1/dim_people.csv", "dim_people"),
    CsvFile("bases_atv_dev_2/bridge_movie_genre.csv", "bridge_movie_genre"),
    CsvFile("bases_atv_dev_2/bridge_movie_company.csv", "bridge_movie_company"),
    CsvFile("bases_atv_dev_2/bridge_movie_person.csv", "bridge_movie_person"),
    CsvFile("bases_atv_dev_2/fact_movies_performance.csv", "fact_movies_performance"),
    CsvFile("bases_atv_dev1/dim_reviews.csv", "dim_reviews"),
    CsvFile("bases_atv_dev_2/movies_reviews.csv", "movie_reviews"),
)


class LoadError(Exception):
    """Interrupção prevista da carga (arquivos ou tabelas ausentes); nada é gravado."""


@dataclass
class TableStats:
    """Contadores de uma tabela para o relatório final."""

    table: str
    read: int = 0
    inserted: int = 0
    ignored: int = 0  # chave já existente no banco
    discarded: int = 0  # linha inválida


@dataclass
class LoadReport:
    """Resultado de uma execução da carga."""

    tables: list[TableStats] = field(default_factory=list)
    # (arquivo, motivo) → números das linhas afetadas
    issues: dict[tuple[str, str], list[int]] = field(default_factory=dict)
    synopses_fixed: int = 0
    elapsed_seconds: float = 0.0

    def add_issue(self, file: str, reason: str, line: int) -> None:
        self.issues.setdefault((file, reason), []).append(line)


def expected_columns(table_name: str) -> list[str]:
    """Colunas que o CSV precisa ter: as da tabela, exceto as preenchidas pelo banco."""

    table = Base.metadata.tables[table_name]
    return [column.name for column in table.columns if column.server_default is None]


def check_files(data_dir: Path) -> None:
    """Confere, antes de gravar qualquer dado, se todos os CSVs existem e têm as colunas."""

    problems: list[str] = []
    for csv_file in CSV_FILES:
        path = data_dir / csv_file.path
        if not path.is_file():
            problems.append(f"{csv_file.path}: arquivo não encontrado em {data_dir}")
            continue

        with path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        missing = [name for name in expected_columns(csv_file.table) if name not in header]
        if missing:
            problems.append(f"{csv_file.path} não tem as colunas: {', '.join(missing)}")

    if problems:
        raise LoadError("\n".join(problems))


def check_tables(conn: Connection) -> None:
    """Confere se as migrações já criaram as tabelas; a carga nunca cria tabelas."""

    existing = set(inspect(conn).get_table_names())
    missing = [csv_file.table for csv_file in CSV_FILES if csv_file.table not in existing]
    if missing:
        raise LoadError(
            f"o banco não tem as tabelas da aplicação ({', '.join(missing)}). "
            "Rode as migrações primeiro:\n  .venv/bin/alembic upgrade head"
        )


def convert_value(column: Column, raw: str) -> str | int | float | Decimal | date | None:
    """Converte o texto do CSV para o tipo da coluna no banco.

    Célula vazia vira None. Valor que não converte lança ValueError; quem chama
    decide se descarta a linha (coluna obrigatória) ou anula o campo (opcional).
    """

    if raw == "":
        return None

    column_type = column.type
    if isinstance(column_type, String):
        return raw  # sem strip: textos ficam como estão no CSV (D-3)
    if isinstance(column_type, Integer):
        return _to_int(raw)
    # Float vem antes de Numeric porque Double/Float são subclasses de Numeric.
    if isinstance(column_type, Float):
        number = float(raw)
        if not math.isfinite(number):
            raise ValueError(f"número inválido: {raw!r}")
        return number
    if isinstance(column_type, Numeric):
        try:
            decimal = Decimal(raw)
        except InvalidOperation as error:
            raise ValueError(f"número inválido: {raw!r}") from error
        if not decimal.is_finite():
            raise ValueError(f"número inválido: {raw!r}")
        return decimal
    if isinstance(column_type, Date):
        return datetime.strptime(raw, "%Y-%m-%d").date()

    raise TypeError(f"tipo de coluna não suportado na carga: {column_type!r}")


def _to_int(raw: str) -> int:
    """Converte para inteiro, aceitando casa decimal zerada ("2375.0" → 2375)."""

    try:
        return int(raw)
    except ValueError:
        number = float(raw)
        if not number.is_integer():
            raise ValueError(f"inteiro inválido: {raw!r}") from None
        return int(number)


def fix_synopsis_quotes(text: str) -> tuple[str, bool]:
    """Desfaz o escape de aspas duplicado da origem (CA-18).

    Sinopses afetadas começam com aspas e têm as aspas internas dobradas, ex.:
    '"Julia ... a ""movie"" ..."'. Retorna o texto e se houve correção.
    """

    if not text.startswith('"'):
        return text, False

    fixed = text[1:]
    # No fim, um número ímpar de aspas inclui a de fechamento (1 ou "" + 1).
    # Um número par é só uma aspa interna dobrada de um texto cortado na origem.
    trailing_quotes = len(fixed) - len(fixed.rstrip('"'))
    if trailing_quotes % 2 == 1:
        fixed = fixed[:-1]
    return fixed.replace('""', '"'), True


BATCH_SIZE = 5_000

# Tabelas referenciadas por chaves estrangeiras e o nome usado no relatório.
PARENT_LABELS: dict[str, str] = {
    "dim_movies": "filme",
    "dim_genres": "gênero",
    "dim_companies": "produtora",
    "dim_people": "pessoa",
}

# Colunas que precisam ter valor único além da chave primária.
UNIQUE_VALUES: dict[str, tuple[str, ...]] = {
    "dim_movies": ("id_filme",),
    "dim_genres": ("nome_genero",),
    "dim_companies": ("nome_produtora",),
    "dim_people": ("nome_pessoa", "tipo_pessoa"),
    "dim_reviews": ("sk_movie_id",),
}


@dataclass
class KnownKeys:
    """O que já é válido: registros do banco mais as linhas aceitas nesta carga."""

    # tabela pai → chaves primárias válidas (para conferir as chaves estrangeiras)
    keys: dict[str, set[str]] = field(
        default_factory=lambda: {table: set() for table in PARENT_LABELS}
    )
    # tabela → valor único → chave primária que já usa esse valor
    unique: dict[str, dict[tuple, tuple]] = field(
        default_factory=lambda: {table: {} for table in UNIQUE_VALUES}
    )


def read_existing_keys(conn: Connection) -> KnownKeys:
    """Lê do banco as chaves e os valores únicos das tabelas pai."""

    known = KnownKeys()
    for table_name in PARENT_LABELS:
        table = Base.metadata.tables[table_name]
        (primary_key,) = table.primary_key.columns
        unique_columns = [table.c[name] for name in UNIQUE_VALUES[table_name]]
        for key, *unique_value in conn.execute(select(primary_key, *unique_columns)):
            known.keys[table_name].add(key)
            known.unique[table_name][tuple(unique_value)] = (key,)
    return known


class _InvalidRow(Exception):
    """Linha que não pode ser gravada; a mensagem é o motivo mostrado no relatório."""


def load_file(
    conn: Connection,
    data_dir: Path,
    csv_file: CsvFile,
    known: KnownKeys,
    report: LoadReport,
) -> None:
    """Lê um CSV, valida cada linha e grava as válidas em lotes."""

    table = Base.metadata.tables[csv_file.table]
    columns = [table.c[name] for name in expected_columns(table.name)]
    file_name = Path(csv_file.path).name
    stats = TableStats(table.name)
    seen_keys: set[tuple] = set()
    batch: list[dict] = []
    accepted = 0
    rows_before = _count_rows(conn, table)

    with (data_dir / csv_file.path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats.read += 1
            try:
                values, nulled = _validate_row(row, table, columns, known, seen_keys)
            except _InvalidRow as error:
                stats.discarded += 1
                report.add_issue(file_name, f"linha descartada: {error}", reader.line_num)
                continue

            for column_name in nulled:
                report.add_issue(
                    file_name, f"campo anulado: {column_name} inválido", reader.line_num
                )
            if table.name == "dim_movies" and values["sinopse"] is not None:
                values["sinopse"], fixed = fix_synopsis_quotes(values["sinopse"])
                report.synopses_fixed += fixed

            _remember(values, table, known, seen_keys)
            batch.append(values)
            accepted += 1
            if len(batch) == BATCH_SIZE:
                _insert_batch(conn, table, batch)
                batch = []

    if batch:
        _insert_batch(conn, table, batch)
    stats.inserted = _count_rows(conn, table) - rows_before
    stats.ignored = accepted - stats.inserted
    report.tables.append(stats)


def _validate_row(
    row: dict,
    table: Table,
    columns: list[Column],
    known: KnownKeys,
    seen_keys: set[tuple],
) -> tuple[dict, list[str]]:
    """Converte e valida uma linha. Retorna os valores e as colunas anuladas (CA-13)."""

    # O DictReader guarda campos a mais sob a chave None e completa os que faltam com None.
    if None in row or None in row.values():
        raise _InvalidRow("número de colunas diferente do cabeçalho")

    values: dict = {}
    nulled: list[str] = []
    for column in columns:
        try:
            value = convert_value(column, row[column.name])
        except ValueError:
            if not column.nullable:
                raise _InvalidRow(f"{column.name} inválido") from None
            value = None
            nulled.append(column.name)
        if value is None and not column.nullable:
            raise _InvalidRow(f"{column.name} vazio")
        values[column.name] = value

    # Regras que o banco garante com CHECK: conferidas antes para não abortar a transação.
    if table.name == "dim_people" and values["tipo_pessoa"] not in models.PERSON_TYPES:
        raise _InvalidRow("tipo_pessoa diferente de Ator, Diretor ou Roteirista")
    if table.name == "movie_reviews" and not 0 <= values["nota"] <= 10:
        raise _InvalidRow("nota fora de 0–10")

    for foreign_key in sorted(table.foreign_keys, key=lambda fk: fk.parent.name):
        parent = foreign_key.column.table.name
        if values[foreign_key.parent.name] not in known.keys[parent]:
            raise _InvalidRow(f"{PARENT_LABELS[parent]} inexistente ou descartado")

    primary_key = _primary_key(values, table)
    if primary_key in seen_keys:
        raise _InvalidRow("chave repetida no arquivo")

    if table.name in UNIQUE_VALUES:
        unique_columns = UNIQUE_VALUES[table.name]
        owner = known.unique[table.name].get(tuple(values[name] for name in unique_columns))
        if owner is not None and owner != primary_key:
            raise _InvalidRow(f"{' + '.join(unique_columns)} já usado por outra chave")

    return values, nulled


def _remember(values: dict, table: Table, known: KnownKeys, seen_keys: set[tuple]) -> None:
    """Registra uma linha aceita, para validar as próximas linhas e arquivos."""

    primary_key = _primary_key(values, table)
    seen_keys.add(primary_key)
    if table.name in UNIQUE_VALUES:
        unique_value = tuple(values[name] for name in UNIQUE_VALUES[table.name])
        known.unique[table.name][unique_value] = primary_key
    if table.name in PARENT_LABELS:
        known.keys[table.name].add(primary_key[0])


def _primary_key(values: dict, table: Table) -> tuple:
    return tuple(values[column.name] for column in table.primary_key.columns)


def _insert_batch(conn: Connection, table: Table, batch: list[dict]) -> None:
    """Grava um lote; linhas cuja chave já existe no banco são puladas (CA-10)."""

    conn.execute(sqlite_insert(table).on_conflict_do_nothing(), batch)


def _count_rows(conn: Connection, table: Table) -> int:
    return conn.execute(select(func.count()).select_from(table)).scalar_one()
