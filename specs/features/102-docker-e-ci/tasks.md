# 102 — Docker e CI — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Concluído (2026-09-27; registrado depois da implementação) |
| Spec   | [`spec.md`](spec.md)                                    |
| Plan   | [`plan.md`](plan.md)                                    |

Registro retroativo: as tasks descrevem o que o desenvolvedor implementou
(commits `6e69130` e `c846203`) e as verificações feitas depois.

## Fase 0 — Containers

- [x] **T-01. Imagem do backend** (CA-2, CA-3, CA-7, CA-8)
  - `backend/Dockerfile`, `backend/docker-entrypoint.sh` e
    `backend/.dockerignore`; `sqlalchemy[asyncio]` no `pyproject.toml`.
  - Problemas encontrados na primeira revisão e corrigidos pelo
    desenvolvedor:
    - `COPY alembic.ini app/ migrations/ ./` copiava o conteúdo das pastas
      sem as pastas (`app.main` não existia);
    - o `docker-entrypoint.sh` não era copiado para a imagem;
    - o shebang estava como `#!bin/sh`.
  - Verificação: o container aplica as migrações, pula a carga quando o
    `.loaded` existe e sobe o uvicorn com um único processo.

- [x] **T-02. Imagem do frontend** (CA-4, CA-5)
  - `frontend/Dockerfile` (Bun + nginx), `frontend/nginx.conf` e
    `frontend/.dockerignore`.
  - Problema encontrado e corrigido: `try_files $uri $ uri/ …` (espaço em
    `$ uri/`).
  - Verificação: `nginx -t` sem erros; `/`, `/filmes/<id>`, `/filmes/novo` e
    um caminho inexistente devolvem o `index.html`.

- [x] **T-03. `docker-compose.yml`** (CA-1, CA-6, CA-8)
  - Serviços `api` e `web`, volume `db-data`, `./data` só para leitura.
  - Problema encontrado e corrigido: a variável de CORS estava como
    `BACKEND_CORS_ORIGIN` (sem o "S"); o navegador em `:8080` seria
    bloqueado.
  - Verificação: a API aceita a origem `http://localhost:8080`, inclusive na
    verificação prévia de um `POST`.

## Fase 1 — CI

- [x] **T-04. Pipeline `.github/workflows/ci.yml`** (CA-9 a CA-16)
  - Jobs `backend` (matriz 3.11 a 3.14), `frontend` e `docker`.
  - Problemas encontrados na primeira revisão e corrigidos:
    - `pip install -e "[.dev]"` em vez de `".[dev]"`;
    - `bun run Build` em vez de `build`;
    - o job `docker` sem `actions/checkout`.
  - Acrescentado depois, a pedido do desenvolvedor: versões da matriz entre
    aspas, passo de formatação separado do lint, `alembic check` e Bun fixo
    em 1.4.0.
  - Verificação: o YAML é válido e a matriz é lida como texto.

## Fase 2 — Documentação

- [x] **T-05. README e CLAUDE.md** (CA-17)
  - `README.md`: "Com Docker" (comandos, endereços, primeira subida, como
    funciona, recarga dos dados), "Integração contínua (CI)" (gatilhos, jobs,
    comandos para conferir localmente) e decisões do Docker.
  - `CLAUDE.md`: comandos de Docker e CI, mapa do código e a armadilha da
    matriz de Python.

## Fase 3 — Verificação

- [x] **T-06. Aplicação nos containers** (CA-1 a CA-8)
  - Contra a stack que o desenvolvedor tinha no ar, só com leituras, sem
    parar nem recriar os containers.
  - **Resultado (2026-09-27):**
    - `/health` responde; catálogo com 95.645 filmes; `X-Cache` alterna
      entre `MISS` e `HIT`;
    - volume com `moviestars.db` e `.loaded`; logs com "Dados já carregados;
      pulando a carga." e as migrações aplicadas;
    - roteiro `check_docker.py` no navegador em `:8080`: **8/8** (catálogo,
      total, busca, detalhes, recarregar `/filmes/<id>`, filtros pela URL,
      formulário com os 19 gêneros, nenhum erro de conexão com a API).
  - As escritas (cadastro, edição, remoção e avaliação) não foram exercidas
    nos containers, para não alterar os dados do desenvolvedor; elas usam as
    mesmas rotas conferidas pelos roteiros da 003 e da 004.

- [x] **T-07. Pipeline simulada** (CA-10 a CA-13, CA-16)
  - Num clone limpo do repositório (commit `6e69130`), com ambiente Python
    novo, rodando os comandos exatamente como no `ci.yml`.
  - **Resultado (2026-09-27):**

    | Job        | Passo                                   | Resultado |
    |------------|-----------------------------------------|-----------|
    | `backend`  | `pip install -e ".[dev]"`               | ok        |
    |            | `ruff check .`                          | All checks passed |
    |            | `ruff format --check .` (\*)            | 35 files already formatted |
    |            | `pytest`                                | 273 passed |
    |            | `alembic upgrade head` (banco vazio)    | 0001 a 0005 aplicadas |
    |            | `alembic check` (\*)                    | No new upgrade operations detected |
    | `frontend` | `bun install --frozen-lockfile`         | 166 pacotes |
    |            | `bun run lint`                          | sem erros |
    |            | `bun run build`                         | ok        |
    | `docker`   | `docker compose build`                  | imagens `api` e `web` construídas |

    (\*) Passos acrescentados depois da simulação; rodaram localmente, com
    os mesmos comandos, sobre o mesmo código e um banco novo.

  - Localmente foi usado o Python 3.14; o 3.11 roda na imagem Docker, e o
    3.12 e o 3.13 ficam para a primeira execução no GitHub. As imagens e o
    clone de teste foram apagados.

## Rastreabilidade

| CA    | Tasks            |
|-------|------------------|
| CA-1  | T-03, T-06       |
| CA-2  | T-01, T-06       |
| CA-3  | T-01, T-06       |
| CA-4  | T-02, T-06       |
| CA-5  | T-02, T-06       |
| CA-6  | T-03, T-06       |
| CA-7  | T-01, T-06       |
| CA-8  | T-01, T-03       |
| CA-9  | T-04             |
| CA-10 | T-04, T-07       |
| CA-11 | T-04, T-07       |
| CA-12 | T-04, T-07       |
| CA-13 | T-04, T-07       |
| CA-14 | T-04             |
| CA-15 | T-04             |
| CA-16 | T-04, T-07       |
| CA-17 | T-05             |
