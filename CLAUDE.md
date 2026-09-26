# CLAUDE.md

Sistema de Avaliação de Filmes (Rocket Lab 2026): módulo administrativo com
backend FastAPI + SQLAlchemy async + SQLite e frontend Vite + React + TypeScript.

**Antes de qualquer tarefa, leia `specs/constitution.md`.** Ela define a stack,
as decisões de domínio (escala de notas, cálculo da média, gêneros, diretor)
e as convenções de código. Não repita nem contradiga essas regras.

## Contexto do desenvolvedor

O desenvolvedor está aprendendo Python/FastAPI e React/TypeScript.

- Ao propor ou implementar algo não óbvio, explique em 1–2 frases o porquê.
- Prefira soluções simples e legíveis a soluções engenhosas.
- Não gere código além do que as tasks pedem.

## Fluxo de trabalho (SDD)

Cada feature vive em `specs/features/NNN-nome-da-feature/` com três arquivos.
Siga as etapas **em ordem** e **pare ao final de cada uma** para aprovação:

1. **Spec** (`spec.md`): histórias de usuário, critérios de aceitação
   numerados (CA-1, CA-2...), casos de borda e "Fora de escopo".
   Sem detalhes de tecnologia. → **Pare e peça revisão.**
2. **Plan** (`plan.md`): endpoints, schemas, consultas, componentes,
   arquivos que serão criados/alterados e seção "Decisões" (com alternativa
   descartada e motivo). → **Pare e peça revisão.**
3. **Tasks** (`tasks.md`): checklist de passos pequenos e verificáveis,
   cada um referenciando os CAs que atende (ex.: `- [ ] Criar rota POST (CA-1, CA-3)`).
   → **Pare e peça revisão.**
4. **Implementação**: execute uma task por vez, marque `- [x]` ao concluir
   e rode os testes relevantes.

Regras:

- Nunca implemente sem `plan.md` aprovado.
- Se a implementação exigir algo diferente do plan, **pare**, explique a
  divergência e proponha a alteração na spec/plan antes de mudar o código.
- Se algo não estiver definido na spec nem na constituição, pergunte em vez
  de supor.

## Comandos

### Backend (`cd backend`)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head          # cria/atualiza as tabelas
.venv/bin/python -m app.movies.load_data          # carga dos CSVs (~35 s; repetível)
.venv/bin/python -m app.movies.load_data --reset  # apaga e recarrega tudo
.venv/bin/uvicorn app.main:app --reload # API em http://localhost:8000/docs
.venv/bin/pytest                        # testes
.venv/bin/ruff check .                  # lint
.venv/bin/ruff format .                 # formatação
.venv/bin/alembic revision --autogenerate -m "descricao"  # nova migração
```

### Frontend (`cd frontend`)

```bash
bun install
bun run dev     # http://localhost:5173
bun run build   # checa tipos e gera o build
bun run lint
```

## Mapa do código

- `backend/app/movies/models.py`: modelos ORM (esquema estrela). Não altere
  sem uma migração Alembic.
- `backend/app/movies/{schemas,service,router}.py`: camadas do domínio
  (ver constituição, seção 5.2).
- `backend/app/api/v1/router.py`: registro dos routers.
- `backend/app/movies/load_data.py`: carga dos CSVs (feature 000), script
  síncrono executado com `python -m`.
- `backend/app/db/session.py`: engine e `get_db`.
- `backend/migrations/versions/`: revisões Alembic.
- `frontend/src/{api,types,pages,components,hooks}/`: ver constituição,
  seção 5.3.
- `specs/`: constituição e features.
- `data/bases_atv_dev1/` e `data/bases_atv_dev_2/`: CSVs de carga inicial
  (versionados). O banco `backend/moviestars.db` ocupa ~550 MB
  depois da carga.

## Armadilhas conhecidas

- **Lazy load em async:** acessar `movie.genres`, `movie.people` ou
  `movie.reviews` sem `selectinload` na consulta gera `MissingGreenlet`.
- **Notas:** banco em 0–10, API e frontend em 1–5 estrelas. A conversão
  fica apenas no `service.py`.
- **Média:** calcular com `AVG` sobre `movie_reviews`; não confiar em
  `dim_reviews`.
- **`id_filme`:** obrigatório e único; gerar UUID4 no backend ao criar filme.
- **Diretor e gênero** não são colunas de `dim_movies` (usar as tabelas bridge).
- **SQLite e chaves estrangeiras:** o `PRAGMA foreign_keys=ON` já é ativado
  em `session.py`; scripts que abrirem conexões próprias precisam ativá-lo
  também, ou o cascade não funciona.

## Limites

- Não faça commits nem push sem pedido explícito.
- Não edite `.env`, não versione `*.db` e não apague `moviestars.db`.
- Não altere migrações já aplicadas; crie uma nova revisão.
- Não instale dependências novas sem registrá-las na seção "Decisões" do plan.
