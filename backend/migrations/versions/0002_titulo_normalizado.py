"""Adiciona o título normalizado (sem acentos e minúsculo) para busca e ordenação.

Revision ID: 0002_titulo_normalizado
Revises: 0001_initial_movie_schema
Create Date: 2026-09-26
"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_titulo_normalizado"
down_revision: str | Sequence[str] | None = "0001_initial_movie_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BATCH_SIZE = 5_000


def _normalize_title(text: str) -> str:
    # Cópia congelada de app.movies.normalization.normalize_title: a migração
    # precisa dar sempre o mesmo resultado, mesmo que a aplicação mude depois.
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def upgrade() -> None:
    # NOT NULL com valor padrão: o SQLite adiciona a coluna sem recriar a tabela.
    op.add_column(
        "dim_movies",
        sa.Column("titulo_normalizado", sa.String(500), nullable=False, server_default=""),
    )

    dim_movies = sa.table(
        "dim_movies",
        sa.column("sk_movie_id", sa.String),
        sa.column("titulo", sa.String),
        sa.column("titulo_normalizado", sa.String),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.select(dim_movies.c.sk_movie_id, dim_movies.c.titulo)).all()
    updates = [
        {"movie_key": key, "normalized": _normalize_title(title)} for key, title in rows
    ]
    statement = (
        dim_movies.update()
        .where(dim_movies.c.sk_movie_id == sa.bindparam("movie_key"))
        .values(titulo_normalizado=sa.bindparam("normalized"))
    )
    for start in range(0, len(updates), BATCH_SIZE):
        conn.execute(statement, updates[start : start + BATCH_SIZE])

    op.create_index(
        "ix_dim_movies_ordem_catalogo",
        "dim_movies",
        ["titulo_normalizado", "ano_lancamento", "sk_movie_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_movies_ordem_catalogo", table_name="dim_movies")
    op.drop_column("dim_movies", "titulo_normalizado")
