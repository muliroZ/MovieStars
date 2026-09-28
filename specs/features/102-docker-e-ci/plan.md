# 102 — Docker e CI — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Concluído (registrado depois da implementação)        |
| Spec        | [`spec.md`](spec.md)                                  |
| Referências | `specs/constitution.md` (seções 3, 6, 7); plan 101 (DEC-8) |

## Visão geral

```text
docker compose up --build -d
 ├─ api  (backend/Dockerfile, python:3.11-slim)        porta 8000
 │    docker-entrypoint.sh:
 │      alembic upgrade head                           (toda subida)
 │      se não existe /app/db/.loaded:
 │        python -m app.movies.load_data --data-dir /data ; touch .loaded
 │      exec uvicorn app.main:app --host 0.0.0.0 --port 8000   (1 worker)
 │    volumes: db-data → /app/db (moviestars.db)   ./data → /data (só leitura)
 └─ web  (frontend/Dockerfile)                          porta 8080 → 80
      estágio 1 (oven/bun:1): bun install --frozen-lockfile; bun run build
      estágio 2 (nginx:alpine): dist/ + nginx.conf (try_files … /index.html)

navegador ──► http://localhost:8080 (web) ──JS──► http://localhost:8000/api/v1 (api)

GitHub Actions (.github/workflows/ci.yml): push na main e pull requests
 ├─ backend  (matriz Python 3.11 · 3.12 · 3.13 · 3.14)
 │    pip install -e ".[dev]" → ruff check → ruff format --check → pytest
 │    → alembic upgrade head (ci.db) → alembic check
 ├─ frontend (Bun 1.4.0)
 │    bun install --frozen-lockfile → bun run lint → bun run build
 └─ docker   (needs: backend, frontend)
      docker compose build
```

## Containers

### `docker-compose.yml` (raiz)

| Serviço | Build                     | Portas      | Ambiente e volumes                                        | CAs |
|---------|---------------------------|-------------|-----------------------------------------------------------|-----|
| `api`   | `backend/Dockerfile`      | `8000:8000` | `DATABASE_URL=sqlite+aiosqlite:////app/db/moviestars.db`; `BACKEND_CORS_ORIGINS=["http://localhost:8080"]`; `ENVIRONMENT=docker`; volume `db-data:/app/db`; `./data:/data:ro` | CA-1 a CA-3, CA-6 a CA-8 |
| `web`   | `frontend/Dockerfile`     | `8080:80`   | `depends_on: api`                                         | CA-1, CA-4, CA-5 |

Os dois serviços usam `restart: always` e nomes fixos (`api` e `web`).

### Backend (`backend/Dockerfile`, `backend/docker-entrypoint.sh`, `backend/.dockerignore`)

- Imagem `python:3.11-slim`, a versão mínima do projeto.
- `pyproject.toml` é copiado e instalado **antes** do código, para que a
  camada das dependências fique em cache enquanto só o código muda. O
  `pip install .` funciona sem o código porque só as dependências importam
  ali; a aplicação roda de `/app` (DEC-6).
- Depois vêm `alembic.ini`, `docker-entrypoint.sh`, `app/` e `migrations/`,
  cada pasta copiada com o próprio nome.
- `ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]` e
  `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`:
  o entrypoint prepara o banco e termina com `exec "$@"`, então o uvicorn
  vira o processo principal do container (recebe os sinais de parada).
- O entrypoint usa `set -e`: se as migrações ou a carga falharem, o
  container para, o marcador `.loaded` não é criado, e a próxima subida
  tenta a carga de novo.
- `.dockerignore`: ambiente virtual, caches, testes, `.env` e bancos (`*.db*`)
  ficam fora da imagem.

### Frontend (`frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`)

- Estágio de build com `oven/bun:1`: `bun install --frozen-lockfile` e
  `bun run build` (que também roda o `tsc`).
- Estágio final com `nginx:alpine`, só com o `dist/` e o `nginx.conf`.
- `nginx.conf`: `try_files $uri $uri/ /index.html`, para que as rotas do
  React Router (`/filmes/...`) abram ao recarregar (CA-5).
- O build usa o `VITE_API_URL` padrão (`http://localhost:8000/api/v1`): quem
  chama a API é o navegador, pela porta publicada, não o container `web`.
- `.dockerignore`: `node_modules/` e `dist/`.

### Dependência (`backend/pyproject.toml`)

- `sqlalchemy[asyncio]` acrescentado (DEC-5).

## CI (`.github/workflows/ci.yml`)

| Item                 | Valor                                                      | CAs |
|----------------------|------------------------------------------------------------|-----|
| Gatilhos             | `push` na `main`; `pull_request`                           | CA-9 |
| `concurrency`        | grupo `ci-${{ github.ref }}`, `cancel-in-progress: true`   | CA-14 |
| `permissions`        | `contents: read`                                           | CA-15 |
| Job `backend`        | `working-directory: backend`; matriz `["3.11", "3.12", "3.13", "3.14"]`; `setup-python` com cache do pip pelo `pyproject.toml`; passos da visão geral | CA-10, CA-11, CA-16 |
| Job `frontend`       | `working-directory: frontend`; `setup-bun` com `bun-version: "1.4.0"`; passos da visão geral | CA-12 |
| Job `docker`         | `needs: [backend, frontend]`; checkout; `docker compose build` | CA-13 |

- As migrações rodam num banco vazio próprio (`DATABASE_URL` apontando para
  `./ci.db`), e o `alembic check` roda depois, no mesmo banco (CA-10).
- Os testes criam os próprios bancos temporários (constituição, seção 6), e
  o CI não tem `.env`: valem os padrões do `Settings` (CA-16).

## Arquivos

| Arquivo                              | Ação                                   |
|--------------------------------------|----------------------------------------|
| `docker-compose.yml`                 | criado                                 |
| `backend/Dockerfile`                 | criado                                 |
| `backend/docker-entrypoint.sh`       | criado                                 |
| `backend/.dockerignore`              | criado                                 |
| `backend/pyproject.toml`             | `sqlalchemy[asyncio]`                  |
| `frontend/Dockerfile`                | criado                                 |
| `frontend/nginx.conf`                | criado                                 |
| `frontend/.dockerignore`             | criado                                 |
| `.github/workflows/ci.yml`           | criado                                 |
| `README.md`                          | seções "Com Docker", "Integração contínua (CI)" e decisões | 
| `CLAUDE.md`                          | comandos de Docker e CI, mapa e armadilha da matriz |

Nenhum código da aplicação, migração ou teste mudou.

## Verificação

Sem testes automatizados novos: a própria CI é a verificação contínua. As
verificações feitas no registro estão nas tasks (T-06 e T-07).

## Decisões

- **DEC-1. Compose com `api` e `web`, sem serviço de banco** (spec, D-1). O
  SQLite é um arquivo; um volume nomeado (`db-data`) o guarda entre
  recriações dos containers.
  *Descartado:* montar o `backend/moviestars.db` local, que misturaria o
  banco do Docker com o de desenvolvimento e dependeria de um arquivo que não
  está no repositório.
- **DEC-2. Migrações a cada subida, carga só na primeira** (spec, D-2), com o
  marcador `.loaded` no volume. Um clone novo funciona sem passo manual, e um
  `git pull` com migração nova só precisa de `docker compose up --build`.
  *Descartado:* carga manual com `docker compose exec`, um passo a mais para
  quem só quer ver a aplicação.
- **DEC-3. Frontend de produção com nginx** (spec, D-3), em dois estágios.
  *Descartado:* o servidor de desenvolvimento do Vite, que exigiria o código
  montado e não representa a aplicação entregue.
- **DEC-4. Um único worker do uvicorn** (plan 101, DEC-8): o `CMD` não passa
  `--workers`, então vale o padrão de um processo.
- **DEC-5. `sqlalchemy[asyncio]` no `pyproject.toml`.** A imagem instala as
  versões mais recentes permitidas (SQLAlchemy 2.1), que já não instalam o
  `greenlet` sozinhas; o modo assíncrono precisa dele. Não é uma biblioteca
  nova, e sim o extra oficial do SQLAlchemy.
- **DEC-6. Dependências antes do código no `Dockerfile` do backend,** para
  aproveitar o cache de camadas do Docker.
- **DEC-7. GitHub Actions com três jobs** (spec, D-4), e o `docker` esperando
  os outros dois (`needs`), para não gastar tempo construindo imagens de uma
  mudança que já falhou.
- **DEC-8. Matriz de Python 3.11 a 3.14** (spec, D-5), com as versões entre
  aspas: sem elas o YAML lê números, e um futuro `3.10` viraria `3.1`.
- **DEC-9. Bun fixo em 1.4.0 e `--frozen-lockfile`,** a mesma versão do
  desenvolvimento, e a instalação falha se o `bun.lock` estiver
  desatualizado.
- **DEC-10. Lint e formatação em passos separados** (`ruff check` e
  `ruff format --check`), para o log mostrar qual dos dois falhou; e
  `alembic check`, a mesma verificação da definição de pronto das features.
- **DEC-11. `concurrency` com cancelamento e `permissions: contents: read`:**
  economiza execuções repetidas e dá à pipeline só a permissão de que ela
  precisa.
- **DEC-12. Nenhuma dependência nova** além do extra da DEC-5; as imagens base
  (`python:3.11-slim`, `oven/bun:1`, `nginx:alpine`) e as actions
  (`checkout`, `setup-python`, `setup-bun`) são as oficiais.

## Riscos

- **Versões não travadas no backend:** uma versão nova de uma dependência
  pode quebrar a imagem ou a CI sem mudança no código (foi o caso do
  `greenlet`, DEC-5). Travar as versões ficou fora do escopo.
- **Python 3.12 e 3.13** só são testados na CI; localmente foram conferidos
  o 3.14 (ambiente de desenvolvimento) e o 3.11 (imagem Docker).
