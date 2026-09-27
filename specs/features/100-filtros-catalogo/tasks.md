# 100 — Filtros e ordenação do catálogo — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Concluído (2026-09-27)                                  |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos de backend rodam em `backend/` e os de frontend em
`frontend/`. "Build e lint passam" significa que `bun run build` e
`bun run lint` terminam sem erros. Os testes de backend ficam em
`tests/test_catalog_filters_api.py` e usam `conftest.py` e `helpers.py`.

## Fase 0 — Índices (backend)

- [x] **T-01. Migração 0004 e índices no `models.py`** (RNF-1, DEC-8)
  - `models.py`:
    - `MovieReview.sk_movie_id` sem `index=True`;
    - índice `ix_movie_reviews_movie_nota (sk_movie_id, nota)`;
    - índice `ix_bridge_movie_genre_genero (sk_genre_id, sk_movie_id)` na
      tabela de associação.
  - `migrations/versions/0004_indices_filtros.py`: cria os dois índices e
    remove `ix_movie_reviews_sk_movie_id`; o `downgrade` desfaz tudo.
  - Verificação:
    - `pytest` passa (inclusive os testes da 002 a 004, que usam a lista e a
      cascata de avaliações);
    - num banco temporário, `alembic upgrade head`, `downgrade -1` e
      `upgrade head` rodam sem erro;
    - `alembic check` não detecta diferenças.

- [x] **T-02. Aplicar a migração 0004 no `moviestars.db`**
  - Verificação:
    - `alembic current` mostra `0004_indices_filtros (head)`;
    - `EXPLAIN QUERY PLAN` do agregado de avaliações usa o índice cobridor, e
      a subconsulta de gênero usa o índice novo;
    - a lista de avaliações de um filme continua usando índice.

## Fase 1 — API de filtros e ordenação (backend)

- [x] **T-03. Schemas `CatalogFilters` e `CatalogQuery`** (CA-5 a CA-8, CA-13, CA-14, CA-21, DEC-2)
  - Campos, padrões e validações da tabela do plan, com mensagens em
    português: faixa de ano; ano inicial maior que o final no campo
    `year_max`.
  - Testes chamando o schema:
    - padrões;
    - listas de `genre` e `status`;
    - ano 1887 e ano atual + 11;
    - `year_min` > `year_max` (erro em `year_max`);
    - valores inválidos de `genre_mode`, `status`, `reviews` e `sort`;
    - `min_stars` 0 e 6.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-04. Filtros no `list_movies`** (CA-3 a CA-10, DEC-3 a DEC-6, DEC-9)
  - Parâmetro `filters` opcional; `_review_stats`, `_needs_stats` e
    `_filter_conditions`; o total com as mesmas condições.
  - Testes (serviço):
    - `any` e `all`;
    - gênero inexistente (vazio com `all`; ignorado entre outros com `any`);
    - filme sem gênero nunca aparece com filtro de gênero;
    - ano só mínimo, só máximo e os dois (inclusivos);
    - dois status;
    - `reviews=with` e `without`;
    - `min_stars` com média 3,96 (entra em 4) e 3,94 (não entra), e filme sem
      avaliação nunca entra;
    - combinação com busca, com `total` e `pages` corretos;
    - sem `filters`, o resultado é idêntico ao da 001.
  - Verificação: `pytest` passa, inclusive os 17 usos de `list_movies` da
    001.

- [x] **T-05. Ordenação no `list_movies`** (CA-13 a CA-16, DEC-7)
  - `_order_by` com os 4 campos, `reverse`, `NULLS LAST` e o desempate.
  - Testes:
    - cada campo nas duas direções;
    - sem ano e sem avaliação no fim nas duas direções;
    - quantidade 0 seguindo a direção;
    - empate desempatado pelo título;
    - três páginas sem repetir filmes.
  - Verificação: `pytest` passa.

- [x] **T-06. Rota com `CatalogQuery`** (CA-19, CA-21)
  - `GET /movies` recebe `Annotated[CatalogQuery, Query()]` e repassa os
    filtros.
  - Testes pelo `client`:
    - `?genre=Drama&genre=Horror&genre_mode=all&year_min=2018&status=Lançado&reviews=with&sort=rating&reverse=true`
      aplica tudo;
    - 422 com as mensagens em português no `loc` certo;
    - sem parâmetros novos, o JSON é igual ao da 001.
  - Verificação: `pytest`, `ruff check .` e `ruff format --check .` passam;
    o OpenAPI lista os parâmetros novos.

- [x] **T-07. Desempenho com os dados reais** (RNF-1)
  - Medir pela API, no `moviestars.db`, os 8 casos da seção "Desempenho" do
    plan, e também a lista de avaliações da 002 (por causa da troca de
    índice).
  - Anotar os tempos na seção "Riscos" do plan.
  - Verificação: todos abaixo de 1 s.

## Fase 2 — Base do frontend

- [x] **T-08. Cliente, API e `useGenres`** (CA-3, DEC-10, DEC-11)
  - `QueryParams` do `client.ts` aceita listas (repetindo a chave) e
    booleanos; `listMovies` recebe os filtros.
  - Criar `hooks/useGenres.ts`; o `GenrePicker` passa a usá-lo, com o mesmo
    comportamento.
  - Verificação: build e lint passam; os roteiros da 003
    (`check_manage.py`, formulário com gêneros) e da 001 continuam passando.

- [x] **T-09. `utils/catalogFilters.ts`** (CA-1, CA-5, CA-13, CA-17, CA-19, CA-20)
  - Criar `CatalogFilters`, `DEFAULT_FILTERS`, `SORT_OPTIONS`,
    `parseFilters`, `writeFilters`, `activeFilterCount`,
    `filtersToApiParams` e `validateYearRange`.
  - Verificação:
    - build e lint passam;
    - um script temporário com `bun` confere a ida e volta pela URL, os
      valores inválidos ignorados, a contagem (a ordenação não conta) e a
      URL limpa sem filtros;
    - o mesmo script compara `validateYearRange` com a validação do backend,
      e as mensagens batem.

- [x] **T-10. `useMovies` com filtros** (CA-11)
  - A chave da requisição inclui os filtros serializados.
  - Verificação: build e lint passam, sem avisos das regras de hooks.

## Fase 3 — Componentes

- [x] **T-11. `CatalogToolbar`** (CA-1, CA-2, CA-13, CA-14)
  - Botão "Filtros (N)" com `aria-expanded`; `<select>` com os rótulos da
    D-11 da spec; botão "Inverter" com `aria-pressed`.
  - Verificação: build e lint passam; conferido na T-15.

- [x] **T-12. `StarInput` com `disabled`** (CA-9)
  - Botões de opção desabilitados e aparência de desabilitado; sem prévia
    ao passar o mouse.
  - Verificação: build e lint passam; o roteiro da 004 (`check_reviews.py`)
    continua passando.

- [x] **T-13. `FilterPanel`** (CA-3 a CA-9, CA-12, DEC-12)
  - O painel tem:
    - Gêneros (`GenrePicker` + "Qualquer um"/"Todos");
    - Ano (estado próprio, espera de 400 ms, erro de faixa, só grava
      valores válidos, acompanha a URL);
    - Status (etiquetas);
    - Avaliações (três opções; "Sem avaliação" limpa o mínimo de estrelas);
    - Mínimo de estrelas (`StarInput` + "Qualquer nota");
    - "Limpar filtros".
  - Verificação: build e lint passam; conferido na T-15.

## Fase 4 — Tela do catálogo

- [x] **T-14. `CatalogPage` com barra, painel e URL** (CA-1, CA-2, CA-10 a CA-12, CA-17 a CA-20, CA-22, CA-23)
  - Filtros lidos da URL; `setFilters` com `push` e volta à página 1.
  - O painel aberto ou fechado fica em estado local.
  - Os gêneros inválidos saem da URL com `replace`, quando o `useGenres`
    carrega.
  - Resumo com " · K filtros ativos"; vazio com filtros mostra a mensagem do
    CA-18 e "Limpar filtros".
  - CSS: painel em uma coluna abaixo de 768 px e em duas a partir daí; barra
    que quebra linha.
  - Verificação: build e lint passam; com a API real, filtrar por "Drama" e
    ordenar pela média mostram o resultado certo, e a URL guarda os dois.

## Fase 5 — Verificação e fechamento

- [x] **T-15. Roteiro no navegador** (CA-1 a CA-23, DEC-13)
  - `check_filters.py` (Playwright, no scratchpad) contra o `moviestars.db`
    real, cobrindo os itens da seção "Frontend" do plan, e as regressões das
    features 001 a 004 numa cópia do banco.
  - Anotar os resultados aqui e apagar a cópia.
  - Verificação: todos os itens ok, com os problemas encontrados corrigidos
    antes de marcar; o `moviestars.db` não muda (a não ser pela migração da
    T-02).
  - **Resultado (2026-09-27):** `check_filters.py` contra a API e o
    `moviestars.db` reais: **56 de 56 verificações ok**, em 3 rodadas
    seguidas.

    | Área | O que foi conferido | CAs |
    |---|---|---|
    | Barra e painel | "Filtros" sem contagem e "Filtros (1)"; 4 opções de ordenação; "Inverter" desligado; painel começa fechado; abrir e fechar não mudam a URL nem pedem filmes | CA-1, CA-2 |
    | Gêneros | 19 em ordem alfabética; chave desabilitada sem gênero; "Qualquer um" e "Todos" com os mesmos filmes da API | CA-3, CA-4 |
    | Ano | uma requisição ao digitar "2020"; "de" maior que "até" e ano fora da faixa mostram o erro sem mudar a lista nem a URL; faixa inclusiva; o erro some | CA-5 |
    | Status, avaliações, estrelas | dois status; com + sem avaliação = catálogo inteiro; mínimo de 4 estrelas (menor média exibida 4,0); "Qualquer nota"; "Sem avaliação" limpa e desabilita as estrelas | CA-6 a CA-9 |
    | Combinação | busca + gênero; mudança volta para a página 1; "Limpar filtros" mantém busca e ordenação | CA-10 a CA-12 |
    | Ordenação | ano nas duas direções; troca de campo mantém o "Inverter"; média maior primeiro; última página pela média só com filmes sem avaliação; ordenação não conta como filtro | CA-13 a CA-15 |
    | Resumo e vazio | " · 1 filtro ativo" e " · 4 filtros ativos"; mensagem de vazio com filtros e "Limpar filtros" mantendo a busca | CA-17, CA-18 |
    | Endereço | recarregar mantém tudo; voltar e avançar levam os campos de ano junto; valores inválidos e faixa invertida ignorados; gênero inexistente sai da URL com `replace` | CA-19, CA-20 |
    | Estados e layout | erro com "Tentar novamente"; 360 px com painel em 1 coluna, 768 e 1280 px em 2, sem rolagem horizontal; console sem erros | CA-22, CA-23 |

    Regressões com a API apontada para uma cópia do banco: **145 de 145**.

    | Roteiro | Resultado |
    |---|---|
    | `check_catalog.py` (001) | 34/34 |
    | `check_catalog_extra.py` (001) | 8/8 |
    | `check_detail.py` (002) | 40/40 |
    | `check_reviews.py` (004) | 24/24 |
    | `check_manage.py` (003) | 39/39 |

    As duas falhas das primeiras rodadas eram do roteiro: ele mandava os
    valores inválidos da URL para a API (422), e conferia a mensagem de vazio
    antes de a tela trocar. Problema corrigido na fase 4: os botões de opção
    do painel herdavam a largura total dos campos globais. O `moviestars.db`
    terminou igual (95.645 filmes, 424.657 pessoas e 43.666 avaliações), e a
    cópia foi apagada.

- [x] **T-16. Documentação** (constituição, seção 6)
  - `README.md`: decisões da 100, a migração 0004 em "Depois de atualizar o
    repositório" e o status.
  - `CLAUDE.md`:
    - mapa com os arquivos novos;
    - armadilhas: o agregado de avaliações só entra quando necessário; o
      `min_stars` usa a média arredondada; a URL do catálogo carrega os
      filtros (`catalogFilters.ts`); o índice de avaliações passou a ser
      `(sk_movie_id, nota)`.
  - Verificação: os caminhos citados existem.

- [x] **T-17. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .`, `ruff format --check .` e
    `alembic check` passam.
  - Frontend: `bun run build` e `bun run lint` passam.
  - CA-1 a CA-23 conferidos contra os testes, a T-07 e a T-15.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                          |
|-------|--------------------------------|
| CA-1  | T-09, T-11, T-14, T-15         |
| CA-2  | T-11, T-14, T-15               |
| CA-3  | T-04, T-08, T-13               |
| CA-4  | T-04, T-13, T-15               |
| CA-5  | T-03, T-04, T-09, T-13         |
| CA-6  | T-03, T-04, T-13               |
| CA-7  | T-03, T-04, T-13               |
| CA-8  | T-03, T-04, T-13               |
| CA-9  | T-12, T-13, T-15               |
| CA-10 | T-04, T-14                     |
| CA-11 | T-10, T-14, T-15               |
| CA-12 | T-13, T-14, T-15               |
| CA-13 | T-03, T-05, T-09, T-11         |
| CA-14 | T-03, T-05, T-11, T-15         |
| CA-15 | T-05                           |
| CA-16 | T-05                           |
| CA-17 | T-09, T-14, T-15               |
| CA-18 | T-14, T-15                     |
| CA-19 | T-06, T-09, T-14, T-15         |
| CA-20 | T-09, T-14, T-15               |
| CA-21 | T-03, T-06                     |
| CA-22 | T-14                           |
| CA-23 | T-14, T-15                     |
| RNF-1 | T-01, T-02, T-07               |
