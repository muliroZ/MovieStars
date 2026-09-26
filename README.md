# MovieStars — Sistema de Avaliação de Filmes

Módulo administrativo de um sistema de avaliação de filmes inspirado no
Letterboxd, desenvolvido para a atividade do Rocket Lab 2026. O administrador
navega pelo catálogo, busca filmes, vê detalhes e a média das avaliações,
cadastra, edita e remove filmes e adiciona avaliações (1 a 5 estrelas).

> Este é o README principal do projeto. O README original do repositório
> base da atividade foi preservado em [`README-BASE.md`](README-BASE.md).

## Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 assíncrono,
  Alembic, SQLite.
- **Frontend:** Vite, React, TypeScript.

Detalhes e justificativas: [`specs/constitution.md`](specs/constitution.md).

## Estrutura

```text
.
├── backend/     # API FastAPI, modelos, migrações Alembic e testes
├── frontend/    # aplicação Vite + React + TypeScript
├── data/        # CSVs de carga inicial do catálogo
├── specs/       # constituição do projeto e specs de cada feature
├── README.md    # este arquivo
└── README-BASE.md
```

## Como executar

### Backend

Requer Python 3.11 ou superior.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head          # cria as tabelas
# carga de dados: comando será documentado ao concluir a feature 000
.venv/bin/uvicorn app.main:app --reload # API em http://localhost:8000/docs
```

Testes e lint:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

### Frontend

```bash
cd frontend
bun install
bun run dev     # http://localhost:5173
```

## Dados

Os CSVs do catálogo estão versionados em `data/`:

- `data/bases_atv_dev1/`: filmes, gêneros, pessoas, produtoras e resumo de
  avaliações;
- `data/bases_atv_dev_2/`: associações filme–gênero/pessoa/produtora,
  métricas de desempenho e avaliações individuais.

São cerca de 1,7 milhão de linhas no total. A rotina de carga é especificada
em [`specs/features/000-carga-de-dados/spec.md`](specs/features/000-carga-de-dados/spec.md).

## Processo de desenvolvimento

O projeto segue Spec-Driven Development: cada feature vive em
`specs/features/NNN-nome/` e passa por `spec.md` → `plan.md` → `tasks.md` →
implementação, com revisão ao final de cada etapa.

| Feature                   | Status          |
|---------------------------|-----------------|
| 000 — Carga de dados      | Spec aprovada   |
| 001 — Catálogo e busca    | Não iniciada    |
| 002 — Detalhes e média    | Não iniciada    |
| 003 — Gerenciar filmes    | Não iniciada    |
| 004 — Avaliações          | Não iniciada    |

## Decisões

### Domínio (valem para todo o projeto)

Resumo; o texto completo está na seção 4 da
[constituição](specs/constitution.md).

- **Notas:** o banco guarda 0–10; a API e a interface usam 1–5 estrelas. A
  conversão acontece só no backend.
- **Média:** calculada na consulta a partir das avaliações individuais; a
  tabela de resumo `dim_reviews` não é usada para exibir médias.
- **Gênero e diretor:** vêm de tabelas de associação, não de colunas do filme.
- **Exclusão de filme:** definitiva, removendo avaliações e vínculos.

### Carga de dados (feature 000)

- **Dados gravados como estão:** inconsistências dos CSVs (ex.: duração 0,
  resumo de avaliações divergente) vão para o banco sem correção. Só é
  descartado ou anulado o que o banco não aceita.
- **Exceção, aspas nas sinopses:** 4.801 sinopses vêm com aspas de escape
  duplicadas; a carga remove as aspas extras. 2.825 delas vêm cortadas na
  origem e não há como recuperar o texto.
- **Duração 0:** 10.160 filmes têm duração 0; a interface exibe "não
  informada".
- **Datas das avaliações importadas:** o CSV não tem data, então todas
  recebem a data da carga.
