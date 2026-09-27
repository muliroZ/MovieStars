"""Índices para os filtros e a ordenação do catálogo (feature 100).

Revision ID: 0004_indices_filtros
Revises: 0003_nome_normalizado_pessoas
Create Date: 2026-09-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_indices_filtros"
down_revision: str | Sequence[str] | None = "0003_nome_normalizado_pessoas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cobridor: média e quantidade de avaliações por filme sem ler a tabela.
    op.create_index(
        "ix_movie_reviews_movie_nota", "movie_reviews", ["sk_movie_id", "nota"]
    )
    # O novo começa pela mesma coluna e atende às mesmas consultas.
    op.drop_index("ix_movie_reviews_sk_movie_id", table_name="movie_reviews")
    # Filmes por gênero (a chave primária da tabela começa por sk_movie_id).
    op.create_index(
        "ix_bridge_movie_genre_genero", "bridge_movie_genre", ["sk_genre_id", "sk_movie_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bridge_movie_genre_genero", table_name="bridge_movie_genre")
    op.create_index("ix_movie_reviews_sk_movie_id", "movie_reviews", ["sk_movie_id"])
    op.drop_index("ix_movie_reviews_movie_nota", table_name="movie_reviews")
