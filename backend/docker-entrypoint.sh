#!/bin/sh

set -e

DB_DIR="${DB_DIR:-/app/db}"
DATA_DIR="${DATA_DIR:-/data}"
MARKER="$DB_DIR/.loaded"

mkdir -p "$DB_DIR"

echo "Aplicando migrações..."
alembic upgrade head

if [ ! -f "$MARKER" ]; then
    echo "Primeira execução: carregando os CSVs de $DATA_DIR (pode levar um tempo)..."
    python -m app.movies.load_data --data-dir "$DATA_DIR"
    touch "$MARKER"
    echo "Carga concluída."
else
    echo "Dados já carregados; pulando a carga."
fi

exec "$@"
