# 101 — Cache de consultas — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Concluído (2026-09-27)                                  |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos rodam em `backend/`. Os testes novos ficam em
`tests/test_cache.py` (classe) e `tests/test_cache_api.py` (API), e usam
`conftest.py` e `helpers.py`.

## Fase 0 — Cache e configuração

- [x] **T-01. Classe `QueryCache` em `app/core/cache.py`** (CA-1, CA-10, CA-12 a CA-14, DEC-1, DEC-4)
  - `MISSING`, `QueryCache` com `get`, `set(key, value, generation)`,
    `clear`, `generation` (só leitura) e `__len__`; atributos públicos
    `enabled`, `ttl_seconds`, `max_entries` e `clock` (padrão
    `time.monotonic`).
  - Testes em `tests/test_cache.py`, com relógio falso:
    - `get` sem valor devolve `MISSING`; `set` e `get`; `None` como valor;
    - expira em `ttl` (um instante antes vale; no limite, não);
    - passando de `max_entries`, sai a menos usada; um `get` a torna a mais
      usada; guardar a mesma chave de novo substitui e a torna a mais usada;
    - `clear` esvazia e incrementa a geração;
    - `set` com geração antiga não guarda.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-02. Configuração e instância global** (CA-15, CA-16, DEC-7, DEC-10)
  - `Settings`: `cache_enabled` (`True`), `cache_ttl_seconds` (300, maior
    que 0) e `cache_max_entries` (256, maior que 0).
  - `.env.example` com `CACHE_ENABLED`, `CACHE_TTL_SECONDS` e
    `CACHE_MAX_ENTRIES`.
  - `query_cache` criado em `app/core/cache.py` a partir do `Settings`.
  - Testes: padrões; `cache_ttl_seconds=0` e `cache_max_entries=0`
    recusados.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-03. Fixture `autouse` no `conftest.py`** (DEC-10)
  - Chama `query_cache.clear()` antes de cada teste.
  - Verificação: `pytest` passa com todos os testes atuais, sem mudar
    nenhum.

## Fase 1 — Leitura com cache

- [x] **T-04. `_cached` e `GET /movies`** (CA-1 a CA-3, CA-5, CA-7, CA-15, CA-17, DEC-2, DEC-5, DEC-6, DEC-9)
  - `router.py`: `_cached(key, response, compute)` e `_catalog_key(query)`;
    `get_movies` com `response: Response`.
  - Testes em `tests/test_cache_api.py`:
    - mesma consulta duas vezes: `MISS` e `HIT`, com o mesmo JSON;
    - `genre` e `status` em outra ordem: `HIT`;
    - mudar `page`, `page_size`, `search`, um filtro, `sort` ou `reverse`:
      `MISS`;
    - 422 sem `X-Cache`; a consulta corrigida vem com `MISS`;
    - `enabled=False`: duas consultas com `BYPASS` e nada guardado;
    - mesma consulta com o cache ligado e desligado: mesmo status e mesmo
      JSON.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-05. `GET /genres` com cache** (CA-4, CA-6, CA-7)
  - `read_genres` com `response: Response` e a chave `"genres"`.
  - Testes: `MISS` e depois `HIT`; detalhes, avaliações e diretores sem
    `X-Cache`.
  - Verificação: `pytest` e `ruff check .` passam; o OpenAPI das duas rotas
    continua com os mesmos parâmetros e o mesmo formato de resposta.

## Fase 2 — Invalidação

- [x] **T-06. Limpeza nas quatro escritas** (CA-8 a CA-11, DEC-3)
  - `service.py`: `query_cache.clear()` depois do `commit` em
    `create_movie`, `update_movie`, `create_review` e, só com
    `rowcount > 0`, em `delete_movie`.
  - Testes:
    - avaliação nova: `GET /movies?sort=rating` vem com `MISS`, com a nova
      média, a nova quantidade e a nova ordem; o mesmo com `min_stars`;
    - cadastrar, atualizar o título e remover: `MISS` com o filme novo, o
      título novo ou sem o filme, e o `total` certo;
    - depois de uma escrita, `GET /genres` e uma consulta sem relação com o
      filme também vêm com `MISS`;
    - avaliação em filme inexistente (404), cadastro com gênero inexistente
      (422), edição e remoção de filme inexistente (404): a consulta
      seguinte continua `HIT`.
  - Verificação: `pytest` passa, inclusive os testes de serviço da 003 e da
    004 sem mudanças.

- [x] **T-07. Corrida, expiração e limite pela API** (CA-12 a CA-14)
  - Testes:
    - o `list_movies` da rota é trocado (`monkeypatch`) por um que chama o
      original e depois `query_cache.clear()`: a resposta vem com `MISS`, e
      a seguinte também;
    - relógio falso: 299 s depois, `HIT`; 300 s depois, `MISS`;
    - `max_entries=2`: três consultas diferentes, e a primeira volta com
      `MISS`.
  - Verificação: `pytest`, `ruff check .` e `ruff format --check .` passam.

## Fase 3 — Verificação e fechamento

- [x] **T-08. Desempenho com os dados reais** (RNF-1, RNF-2)
  - Pela API, no `moviestars.db` (só leituras), 5 execuções de cada, com a
    API reiniciada antes de cada execução:
    - `sort=rating`, última página;
    - `sort=reviews`, última página;
    - sem filtros, página 1;
    - `GET /genres`.
  - Anotar o pior `MISS` e o pior `HIT` de cada consulta na seção "Riscos"
    do plan.
  - Verificação: todo `HIT` da última página por média abaixo de 10 ms; os
    `MISS` próximos dos tempos do plan 100.

- [x] **T-09. Regressões no navegador** (CA-8, CA-9, CA-17)
  - Roteiros da 001 a 004 e da 100 numa cópia do banco, com o cache ligado.
    As escritas da 003 e da 004 conferem, pela tela, que o catálogo mostra
    os dados novos logo depois de cada alteração.
  - Anotar os resultados aqui e apagar a cópia.
  - Verificação: todos os itens ok; o `moviestars.db` não muda.
  - **Resultado (2026-09-27):** API com o cache ligado, apontada para uma
    cópia do `moviestars.db`.

    | Roteiro | Resultado |
    |---|---|
    | `check_cache_ui.py` (101, novo) | 10/10, em 3 rodadas |
    | `check_catalog.py` (001) | 34/34 |
    | `check_catalog_extra.py` (001) | 8/8 |
    | `check_filters.py` (100) | 56/56 |
    | `check_detail.py` (002) | 40/40 |
    | `check_reviews.py` (004) | 24/24 |
    | `check_manage.py` (003) | 39/39 |

    `check_cache_ui.py` confere, pela tela, que o catálogo mostra os dados
    novos logo depois de cada alteração:
    - a mesma busca vem com `MISS` e depois `HIT`;
    - depois de uma avaliação nova, a volta ao catálogo vem com `MISS` e
      mostra "5,0 de 5 estrelas, 1 avaliação";
    - depois da edição, a busca pelo título novo vem com `MISS` e acha o
      filme;
    - depois da remoção, a volta ao catálogo vem com `MISS` e sem o filme.

    Ajustes feitos nos roteiros, não na aplicação:
    - `check_cache_ui.py` anotava os cabeçalhos depois de a aplicação já ter
      voltado ao catálogo após a remoção; agora espera essa resposta;
    - `check_filters.py` esperava só o total no resumo, que é o mesmo em
      todas as ordenações. Com as respostas do cache mais rápidas, comparava
      a lista antes de a tela trocar; agora espera também o primeiro título.
      Depois do ajuste, as falhas de ordenação não voltaram.

    Algumas rodadas de `check_filters.py` acusaram erros
    `ERR_NETWORK_CHANGED` no console. As requisições que falharam eram só os
    pôsteres externos (`image.tmdb.org`), por instabilidade da rede da
    máquina; a API não teve falhas além do bloqueio proposital do CA-22. O
    `moviestars.db` terminou igual (95.645 filmes, 424.657 pessoas e 43.666
    avaliações), e a cópia foi apagada.

- [x] **T-10. Documentação** (constituição, seção 6)
  - `README.md`:
    - seção curta sobre o cache: o que é guardado, quando é descartado, o
      cabeçalho `X-Cache` e as três variáveis;
    - não usar `--workers` maior que 1;
    - decisões da 101 e o status.
  - `CLAUDE.md`:
    - mapa com `app/core/cache.py`;
    - armadilhas: toda escrita nova no serviço chama `query_cache.clear()`
      depois do `commit`; testes que gravam pela sessão entre duas consultas
      da API limpam o cache; um único worker.
  - Verificação: os caminhos citados existem.

- [x] **T-11. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .`, `ruff format --check .` e
    `alembic check` passam.
  - Frontend (não muda): `bun run build` e `bun run lint` continuam
    passando.
  - CA-1 a CA-17 conferidos contra os testes, a T-08 e a T-09.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                          |
|-------|--------------------------------|
| CA-1  | T-01, T-04                     |
| CA-2  | T-04                           |
| CA-3  | T-04                           |
| CA-4  | T-05                           |
| CA-5  | T-04                           |
| CA-6  | T-05                           |
| CA-7  | T-04, T-05                     |
| CA-8  | T-06, T-09                     |
| CA-9  | T-06, T-09                     |
| CA-10 | T-01, T-06                     |
| CA-11 | T-06                           |
| CA-12 | T-01, T-07                     |
| CA-13 | T-01, T-07                     |
| CA-14 | T-01, T-07                     |
| CA-15 | T-02, T-04                     |
| CA-16 | T-02                           |
| CA-17 | T-04, T-09                     |
| RNF-1 | T-08                           |
| RNF-2 | T-08                           |
