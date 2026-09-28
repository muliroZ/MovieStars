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
.venv/bin/alembic upgrade head          # cria/atualiza as tabelas (rode após cada git pull)
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

### Docker (na raiz)

```bash
docker compose up --build -d    # constrói e sobe: web em http://localhost:8080, API em :8000
docker compose logs -f api      # 1ª subida: migrações + carga dos CSVs antes do uvicorn
docker compose ps               # situação dos containers
docker compose down             # para os containers (o banco fica no volume db-data)
docker compose down -v          # para e APAGA o banco do Docker (recarrega na próxima subida)
docker compose exec api python -m app.movies.load_data --data-dir /data --reset  # recarga
docker compose restart api      # esvazia o cache de consultas
```

O banco do Docker (volume `db-data`) é separado do `backend/moviestars.db`;
a API do Docker só aceita CORS de `http://localhost:8080`; as portas 8000 e
8080 precisam estar livres (pare os servidores locais antes).

### CI (antes de dar push)

A pipeline (`.github/workflows/ci.yml`) roda em push na `main` e em pull
requests. Para ela passar, estes comandos precisam passar localmente:

```bash
# backend/
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
DATABASE_URL=sqlite+aiosqlite:///./ci.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite+aiosqlite:///./ci.db .venv/bin/alembic check
rm ci.db
# frontend/
bun install --frozen-lockfile && bun run lint && bun run build
# raiz
docker compose build
```

## Mapa do código

- `backend/app/movies/models.py`: modelos ORM (esquema estrela). Não altere
  sem uma migração Alembic.
- `backend/app/movies/{schemas,service,router}.py`: camadas do domínio
  (ver constituição, seção 5.2).
- `backend/app/api/v1/router.py`: registro dos routers.
- `backend/app/movies/load_data.py`: carga dos CSVs (feature 000), script
  síncrono executado com `python -m`.
- `backend/app/movies/normalization.py`: `normalize_title` (sem acentos e
  maiúsculas), usado na busca e na ordem do catálogo (feature 001).
- `backend/app/core/cache.py`: `QueryCache` e a instância `query_cache`
  (feature 101). O router lê o cache em `GET /movies` e `GET /genres`
  (`_cached`, cabeçalho `X-Cache`); o serviço o limpa depois de cada escrita.
- `backend/tests/conftest.py`: fixtures `session` e `client` sobre um SQLite
  temporário; reutilize nos testes de novos endpoints.
- `backend/tests/helpers.py`: `add_movie(...)` monta filmes de teste (gêneros,
  pessoas, produtoras, métricas, avaliações com data) pelo ORM.
- `backend/app/db/session.py`: engine e `get_db`.
- `backend/migrations/versions/`: revisões Alembic.
- `frontend/src/{api,types,pages,components,hooks}/`: ver constituição,
  seção 5.3. `api/client.ts` é o único lugar com `fetch`; cada componente
  tem seu `.css` ao lado; variáveis de cor em `src/index.css`.
- `frontend/src/utils/format.ts`: `formatDate`, `formatDateTime`,
  `formatDuration`, `formatMoney` (pt-BR). Componentes reutilizáveis:
  `Poster` (imagem padrão), `StarRating`, `NameList` (10 nomes + "Mostrar
  todos"), `FinancialTable`, `ReviewList`.
- Rotas do frontend: `/` (catálogo), `/filmes/novo` (cadastro),
  `/filmes/:skMovieId` (detalhes) e `/filmes/:skMovieId/editar` (edição). O
  cartão passa `state.catalogSearch`, lido por `utils/navigation.ts`, para o
  "Voltar ao catálogo".
- `frontend/src/utils/movieForm.ts`: validação do formulário de filme (mesmas
  regras e mensagens do `MovieInput` do backend) e conversão para a API.
  Componentes do formulário: `GenrePicker`, `DirectorPicker`, `ConfirmDialog`;
  mensagens de sucesso com `useFlash()` / `FlashProvider`.
- `backend/app/core/errors.py`: tradução das mensagens de validação (422)
  para o português.
- Avaliações (feature 004): `frontend/src/utils/reviewForm.ts` (validação,
  espelho do `ReviewInput`), `StarInput` (estrelas como botões de opção
  nativos) e `ReviewForm`, que entra no `ReviewList` pela propriedade `form`.
- Filtros do catálogo (feature 100): `frontend/src/utils/catalogFilters.ts`
  (leitura e gravação na URL, contagem, validação dos anos), `useGenres`,
  `CatalogToolbar` (botão "Filtros", ordenação, "Inverter") e `FilterPanel`.
  No backend, `CatalogFilters`/`CatalogQuery` em `schemas.py` e
  `_filter_conditions`/`_order_by` em `service.py`.
- Docker: `docker-compose.yml` (serviços `api` e `web`), `backend/Dockerfile`
  com `backend/docker-entrypoint.sh` (migrações a cada subida, carga só na
  primeira, marcada por `.loaded` no volume) e `frontend/Dockerfile` com
  `frontend/nginx.conf` (build com Bun, nginx com fallback para `index.html`).
- `.github/workflows/ci.yml`: pipeline de CI com os jobs `backend` (matriz
  Python 3.11 a 3.14), `frontend` (Bun 1.4.0) e `docker` (só depois dos
  outros dois).
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
- **`titulo_normalizado`:** é preenchido sozinho só no **insert** (default do
  SQLAlchemy). Ao **editar** `titulo`, atualize também
  `titulo_normalizado = normalize_title(titulo)`, senão a busca e a ordem do
  catálogo ficam erradas para aquele filme.
- **Ordem da busca/catálogo:** use `titulo_normalizado, ano_lancamento,
  sk_movie_id` (coberta pelo índice `ix_dim_movies_ordem_catalogo`).
- **Títulos com aspas:** a carga corrige os 55 títulos com defeito de aspas
  (`fix_title_quotes`, spec 000, CA-19), e a migração 0005 faz o mesmo nos
  bancos já carregados, só em títulos com aspa inicial **e** aspas dobradas.
  Não aplique a correção de novo num banco já corrigido: `"Blessed"` e
  `"Truelove: The Film"` têm aspas legítimas. Nomes de pessoas e produtoras
  com trechos de sinopse continuam como estão.
- **Datas no frontend:** `data_lancamento` ("AAAA-MM-DD") é formatada
  dividindo o texto (`formatDate`); `new Date("2017-02-01")` vira 31/01 no
  fuso do Brasil. `created_at` é gravado em UTC sem fuso pelo SQLite; o
  serviço o devolve com `Z` e o frontend usa `formatDateTime`.
- **Conversão para estrelas:** use `_to_stars` do `service.py` para médias e
  para notas individuais (mesmo arredondamento em todo lugar).
- **Lucro:** o serviço devolve `lucro_*` como `null` quando falta orçamento
  ou receita (spec 002, D-5); o banco não é alterado.
- **`nome_normalizado` (dim_people):** como `titulo_normalizado`, só é
  preenchido no insert. Nomes de pessoas não são editados pela aplicação.
- **Edição de filme:** `movie.people` guarda diretores, roteiristas e atores;
  o formulário troca só os diretores (`update_movie`). Não substitua a lista
  inteira.
- **Remoção de filme:** é um `DELETE` direto; os dependentes somem pelo
  `ON DELETE CASCADE` (precisa do `PRAGMA foreign_keys=ON`).
- **Validação duplicada:** regras e mensagens do formulário estão em
  `backend/app/movies/schemas.py` (`MovieInput`) e em
  `frontend/src/utils/movieForm.ts`. Mudou uma, mude a outra.
- **Mensagens de 422:** tipos novos de erro do Pydantic precisam de tradução
  em `core/errors.py` (senão caem em "Valor inválido.").
- **Escala das notas:** `_to_nota` (estrelas → nota, ×2) e `_to_stars`
  (nota → estrelas, ÷2) no `service.py` são as únicas conversões; não
  converta em outro lugar.
- **Atualizar sem piscar:** para refletir uma mudança na mesma tela, use
  `useMovie().refresh()` e `useMovieReviews().reload()`; o `retry()` volta ao
  estado "carregando" e desmonta a página (serve para telas de erro).
- **`created_at` com precisão de 1 s:** avaliações criadas no mesmo segundo
  empatam na ordem (desempate pela chave). Em testes, crie as avaliações
  antigas com `created_at` explícito.
- **Agregado de avaliações só quando precisa:** `list_movies` junta a
  subconsulta `_review_stats` só quando precisa: no total, com `reviews=with`
  ou `min_stars` (`_filters_need_stats`); na página, também ao ordenar por
  média ou quantidade (`_needs_stats`). "Sem avaliação" usa `NOT EXISTS`.
  A página ordena as chaves primeiro e carrega os filmes depois (plan 100,
  DEC-15). Não junte o agregado em toda consulta.
- **`min_stars` usa a média arredondada** (`ROUND(AVG(nota) / 2, 1)`), a
  mesma de `_to_stars`: um filme exibido com 4,0 entra em 4 estrelas.
- **URL do catálogo carrega os filtros:** use `writeFilters`/`parseFilters`
  (`catalogFilters.ts`) ao montar endereços do catálogo, senão os filtros se
  perdem. Os nomes na URL são os mesmos da API.
- **Índice de avaliações:** desde a migração 0004 é
  `ix_movie_reviews_movie_nota (sk_movie_id, nota)`, que cobre a lista por
  filme e o agregado; o antigo `ix_movie_reviews_sk_movie_id` não existe mais.
- **Cache de consultas:** toda escrita nova no serviço precisa chamar
  `query_cache.clear()` logo depois do `commit` (e só se algo mudou), senão o
  catálogo mostra dados velhos por até 5 minutos. Testes que gravam pela
  `session` entre duas consultas da API precisam chamar `query_cache.clear()`
  (o `conftest.py` só limpa no início de cada teste). A API roda com um único
  worker, porque o cache é por processo.
- **CI em Python 3.11 a 3.14:** o código precisa rodar no 3.11 (o mínimo do
  `pyproject.toml` e a versão da imagem Docker). Não use sintaxe mais nova,
  como os genéricos `def f[T](...)` e `class C[T]` do 3.12; use `TypeVar`.
  Mudou um modelo? Crie a migração, ou o `alembic check` do CI falha.

## Limites

- Não faça commits nem push sem pedido explícito.
- Não edite `.env`, não versione `*.db` e não apague `moviestars.db`.
- Não altere migrações já aplicadas; crie uma nova revisão.
- Não instale dependências novas sem registrá-las na seção "Decisões" do plan.
