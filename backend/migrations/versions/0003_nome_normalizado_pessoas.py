"""Adiciona o nome normalizado das pessoas (sem acentos e minúsculo) para a busca.

Revision ID: 0003_nome_normalizado_pessoas
Revises: 0002_titulo_normalizado
Create Date: 2026-09-26
"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_nome_normalizado_pessoas"
down_revision: str | Sequence[str] | None = "0002_titulo_normalizado"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BATCH_SIZE = 5_000


def _normalize(text: str) -> str:
    # Cópia congelada de app.movies.normalization.normalize_title: a migração
    # precisa dar sempre o mesmo resultado, mesmo que a aplicação mude depois.
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def upgrade() -> None:
    # NOT NULL com valor padrão: o SQLite adiciona a coluna sem recriar a tabela.
    op.add_column(
        "dim_people",
        sa.Column("nome_normalizado", sa.String(255), nullable=False, server_default=""),
    )

    dim_people = sa.table(
        "dim_people",
        sa.column("sk_person_id", sa.String),
        sa.column("nome_pessoa", sa.String),
        sa.column("nome_normalizado", sa.String),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.select(dim_people.c.sk_person_id, dim_people.c.nome_pessoa)).all()
    updates = [{"person_key": key, "normalized": _normalize(name)} for key, name in rows]
    statement = (
        dim_people.update()
        .where(dim_people.c.sk_person_id == sa.bindparam("person_key"))
        .values(nome_normalizado=sa.bindparam("normalized"))
    )
    for start in range(0, len(updates), BATCH_SIZE):
        conn.execute(statement, updates[start : start + BATCH_SIZE])

    op.create_index(
        "ix_dim_people_tipo_nome_normalizado",
        "dim_people",
        ["tipo_pessoa", "nome_normalizado"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_people_tipo_nome_normalizado", table_name="dim_people")
    op.drop_column("dim_people", "nome_normalizado")
