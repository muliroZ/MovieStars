"""Carga inicial do catálogo a partir dos CSVs da pasta `data/`.

Uso (de dentro de `backend/`):

    .venv/bin/python -m app.movies.load_data [--data-dir PASTA] [--reset]

A carga roda em uma única transação: ou todos os arquivos são gravados, ou
nada é gravado. Ver `specs/features/000-carga-de-dados/`.
"""

from dataclasses import dataclass, field
from pathlib import Path

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
