"""Corrige os títulos com o defeito de aspas da origem (spec 000, CA-19 e D-5).

Revision ID: 0005_titulos_com_aspas
Revises: 0004_indices_filtros
Create Date: 2026-09-27
"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_titulos_com_aspas"
down_revision: str | Sequence[str] | None = "0004_indices_filtros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Cópias congeladas de app.movies.load_data.fix_title_quotes e de
# app.movies.normalization.normalize_title: a migração precisa dar sempre o
# mesmo resultado, mesmo que a aplicação mude depois.
def _fix_title(text: str) -> str:
    fixed = text[1:]
    trailing_quotes = len(fixed) - len(fixed.rstrip('"'))
    if trailing_quotes % 2 == 1:
        fixed = fixed[:-1]
    fixed = fixed.replace('""', '"')
    for index, char in enumerate(fixed):
        if char.isalpha():
            return fixed[:index] + char.upper() + fixed[index + 1 :]
    return fixed


def _normalize_title(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def upgrade() -> None:
    dim_movies = sa.table(
        "dim_movies",
        sa.column("sk_movie_id", sa.String),
        sa.column("titulo", sa.String),
        sa.column("titulo_normalizado", sa.String),
    )
    conn = op.get_bind()
    # Só os títulos com a marca do defeito: aspa inicial e aspas dobradas. Assim um
    # título já corrigido pela carga (ex.: '"Blessed"') não é corrigido de novo.
    rows = conn.execute(
        sa.select(dim_movies.c.sk_movie_id, dim_movies.c.titulo).where(
            dim_movies.c.titulo.startswith('"', autoescape=True),
            dim_movies.c.titulo.contains('""', autoescape=True),
        )
    ).all()
    updates = []
    for key, title in rows:
        fixed = _fix_title(title)
        updates.append({"movie_key": key, "title": fixed, "normalized": _normalize_title(fixed)})
    if updates:
        conn.execute(
            dim_movies.update()
            .where(dim_movies.c.sk_movie_id == sa.bindparam("movie_key"))
            .values(titulo=sa.bindparam("title"), titulo_normalizado=sa.bindparam("normalized")),
            updates,
        )


def downgrade() -> None:
    # Correção de dados: não há como saber depois quais títulos foram alterados.
    pass
