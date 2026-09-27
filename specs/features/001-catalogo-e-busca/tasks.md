# 001 — Catálogo e busca — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Concluído (2026-09-26)                                  |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos de backend rodam em `backend/` e os de frontend em
`frontend/`. Cada task de backend já inclui os testes que a cobrem.

Quando uma task de frontend diz "build e lint passam", significa que
`bun run build` e `bun run lint` terminam sem erros.

## Fase 0 — Título normalizado (backend)

- [x] **T-01. `normalize_title`** (CA-2, CA-11)
  - Criar `app/movies/normalization.py` com a função do plan.
  - Testes em `tests/test_normalization.py`:
    - `"À La Recherche"` vira `"a la recherche"`;
    - `"AÇÃO"` e `"ação"` viram `"acao"`;
    - `"Straße"` vira `"strasse"`;
    - aspas, espaços, dígitos e caracteres não latinos continuam iguais.
  - Verificação: `pytest tests/test_normalization.py` e `ruff check .` passam.

- [x] **T-02. Coluna `titulo_normalizado`, índice e migração 0002** (CA-2)
  - Em `models.py`: coluna com `default` calculado e `server_default=""`, e
    o índice `ix_dim_movies_ordem_catalogo` em `__table_args__`.
  - Criar `migrations/versions/0002_titulo_normalizado.py`: adicionar a
    coluna, preencher em lotes com a cópia própria da normalização e criar o
    índice. O `downgrade` desfaz tudo.
  - Testes:
    - um filme inserido pelo ORM recebe `titulo_normalizado`;
    - em `test_load_data.py`, depois de `run_load` todos os filmes têm a
      coluna preenchida (ex.: `m1` → `"cidade de deus"`).
  - Verificação: `pytest` e `ruff check .` passam; `alembic upgrade head`
    seguido de `alembic downgrade -1` e de novo `upgrade head`, num banco
    temporário apontado por `DATABASE_URL`, roda sem erro.

- [x] **T-03. Aplicar a migração no `moviestars.db`** (CA-2)
  - Rodar `.venv/bin/alembic upgrade head`.
  - Verificação:
    - `alembic current` mostra `0002_titulo_normalizado (head)`;
    - nenhuma linha tem `titulo_normalizado` vazio;
    - "À La Recherche" tem `titulo_normalizado = 'a la recherche'`;
    - o plano da consulta ordenada (`EXPLAIN QUERY PLAN`) usa o índice
      novo.

## Fase 1 — API de listagem (backend)

- [x] **T-04. Fixtures de teste da API** (constituição, seção 6)
  - Criar `tests/conftest.py`:
    - banco SQLite temporário assíncrono com `create_all`;
    - substituição de `get_db` com `app.dependency_overrides`, removida ao
      fim do teste;
    - fixture `client` com `httpx.AsyncClient` + `ASGITransport`;
    - fixture `session` para inserir dados pelo ORM.
  - Verificação: um teste confere que `GET /health` responde pelo `client`
    e que o banco temporário começa vazio; `pytest` passa.

- [x] **T-05. Schemas e listagem paginada e ordenada** (CA-1, CA-2, CA-3, CA-24)
  - `schemas.py` com `MovieListItem` e `MoviePage`.
  - Em `service.py`, `list_movies` com total, `pages`, ordem por título
    normalizado, ano e chave, `offset` e `limit`. Nesta task, sem busca e
    sem avaliações: `media_estrelas` vem `null`, e gêneros e diretores vêm
    vazios.
  - Testes chamando o serviço com a `session`:
    - 25 filmes resultam em página 1 com 20 itens, `total` 25 e `pages` 2;
    - a página 2 tem 5 itens;
    - a página 3 vem vazia, com `total` e `pages` corretos;
    - banco vazio dá `total` 0 e `pages` 0;
    - "À La Recherche" fica entre "A Dark Place" e "Abc";
    - dois filmes "Rings" (2017 e 2005) saem com 2005 primeiro.
  - Verificação: `pytest` passa.

- [x] **T-06. Busca** (CA-10, CA-11, CA-12, CA-13, CA-15)
  - Filtro com `normalize_title(search.strip())` e
    `contains(..., autoescape=True)`.
  - Testes:
    - "ring" encontra "Rings" e "The Lord of the Rings";
    - "acao", "AÇÃO" e "Ação" dão o mesmo resultado;
    - `"  ring  "` equivale a "ring";
    - `"   "` equivale a sem busca;
    - "100%" encontra só "100% Lobo" e não "1000 Dias";
    - "a_b" não encontra "axb";
    - a busca tem paginação e ordem iguais às do catálogo.
  - Verificação: `pytest` passa.

- [x] **T-07. Média, gêneros e diretores** (CA-6, CA-7)
  - Consulta agregada das avaliações dos filmes da página;
    `media_estrelas = round(avg / 2, 1)`.
  - `selectinload` de gêneros e pessoas; diretores filtrados por tipo e em
    ordem alfabética.
  - Testes:
    - notas 9.0 e 6.0 dão 3,8 estrelas e 2 avaliações;
    - filme sem avaliações dá `null` e 0;
    - gêneros em ordem alfabética;
    - um ator do filme não aparece em `diretores`;
    - dois diretores saem em ordem alfabética;
    - filme sem gênero e sem diretor dá listas vazias.
  - Verificação: `pytest` passa.

- [x] **T-08. Rota `GET /api/v1/movies`** (CA-1, CA-25, CA-26)
  - `router.py` com `Query` validado e `response_model=MoviePage`;
    registrar em `app/api/v1/router.py` com o prefixo `/movies`.
  - Testes pelo `client`:
    - caminho feliz com o formato completo da resposta;
    - `page=0`, `page_size=0`, `page_size=101` e `search` com 201
      caracteres dão 422;
    - `search` com 200 caracteres dá 200.
  - Verificação: `pytest` e `ruff check .` passam; `/docs` mostra o
    endpoint com os três parâmetros.

- [x] **T-09. Desempenho com os dados reais** (RNF-1)
  - Com o `moviestars.db` migrado, medir o tempo de resposta de
    `GET /api/v1/movies` para:
    - página 1;
    - última página (4.783);
    - `search=ring`;
    - `search=a`;
    - `search=a&page=` com a última página da busca.
  - Anotar os tempos na seção "Riscos" do plan.
  - Verificação: todos abaixo de 1 s.

## Fase 2 — Base do frontend

- [x] **T-10. Dependência e configuração** (DEC-8, DEC-9)
  - `bun add react-router-dom`.
  - `"strict": true` em `tsconfig.app.json`.
  - Criar `src/vite-env.d.ts` com o tipo de `VITE_API_URL`.
  - `lang="pt-BR"` em `index.html`.
  - Criar `public/poster-placeholder.svg`.
  - Verificação: build e lint passam; `package.json` lista
    `react-router-dom`.

- [x] **T-11. Tipos e cliente da API** (CA-22)
  - `src/types/movie.ts` (`MovieListItem`, `Page<T>`).
  - `src/api/client.ts` (`API_URL`, `apiGet`, `ApiError` com mensagem em
    português para falha de rede e para resposta de erro).
  - `src/api/movies.ts` (`listMovies`).
  - Verificação: build e lint passam; nenhum `any` no código
    (`grep -rn "any" src` não encontra tipos `any`).

- [x] **T-12. Hooks `useDebounce` e `useMovies`** (CA-14, CA-21, CA-22)
  - `useDebounce(valor, 300)`.
  - `useMovies(page, search)`: status `loading`, `error` ou `success`,
    `retry()` e cancelamento da requisição anterior com `AbortController`.
  - Verificação: build e lint passam, sem avisos da regra de dependências
    dos hooks.

- [x] **T-13. Rotas e `NotFoundPage`** (CA-9, DEC-12)
  - `BrowserRouter` em `main.tsx`; `App.tsx` com `/` → `CatalogPage` (por
    enquanto um título provisório) e `*` → `NotFoundPage`.
  - Verificação: build e lint passam; com `bun run dev`, `/` abre a página
    do catálogo e `/filmes/qualquer` mostra "Página não encontrada" com
    link de volta.

## Fase 3 — Componentes

- [x] **T-14. `StarRating`** (CA-6, CA-7)
  - 5 estrelas com preenchimento proporcional (meia estrela), número com 1
    casa em pt-BR ("3,5") e "N avaliações". Sem média, mostra "Sem
    avaliações".
  - Verificação: build e lint passam; na página provisória, 0, 2,5, 3,8 e
    5 estrelas e o caso sem média aparecem corretamente.

- [x] **T-15. `MovieCard`** (CA-6, CA-8, CA-9)
  - O cartão mostra:
    - o pôster, trocado pela imagem padrão em `onError` ou quando vier
      `null`;
    - o título cortado em até 2 linhas, com `title` para o texto completo;
    - o ano, ou "Ano não informado";
    - o `StarRating`;
    - os gêneros (3 + "+N" ou "Sem gênero");
    - os diretores (2 + "e mais N" ou "Diretor não informado").
  - O cartão inteiro é um `Link` para `/filmes/:skMovieId`.
  - Verificação: build e lint passam; na página provisória, com dados
    fixos, aparecem os casos de 11 gêneros, 3 diretores, sem pôster, pôster
    quebrado e título de 151 caracteres.

- [x] **T-16. `SearchBar`** (CA-17, CA-26)
  - Campo com rótulo acessível, `maxLength=200` e botão "Limpar" visível
    quando há texto.
  - Verificação: build e lint passam; o campo não aceita o 201º caractere.

- [x] **T-17. `Pagination`** (CA-3, CA-4)
  - Primeira, anterior, "Página X de Y" (números em pt-BR), próxima e
    última, com os botões dos limites desabilitados.
  - Verificação: build e lint passam; com Y = 1, os quatro botões ficam
    desabilitados.

- [x] **T-18. Estados da tela** (CA-21, CA-22, CA-23, CA-24)
  - `LoadingState`, `ErrorState` (mensagem + "Tentar novamente") e
    `EmptyState` (mensagem + ação opcional).
  - Verificação: build e lint passam.

## Fase 4 — Tela do catálogo

- [x] **T-19. `CatalogPage`** (CA-1, CA-3, CA-5, CA-12, CA-15, CA-16, CA-18, CA-19, CA-20, CA-23, CA-24)
  - Lê `page` (inválido vale 1) e `search` da URL, e grava sem os valores
    padrão.
  - O campo de busca tem estado local; o valor com debounce vai para a URL
    e zera a página; o campo acompanha a URL quando ela muda pelo voltar.
  - Resumo:
    - "N filmes" sem busca;
    - "N filmes encontrados para "termo"" com busca;
    - "1 filme" no singular.
  - Estados:
    - carregando;
    - erro com "Tentar novamente";
    - catálogo vazio;
    - busca sem resultado com "Limpar busca";
    - página além da última com link para a página 1.
  - Rolagem ao topo ao trocar de página.
  - Remover a página provisória usada nas tasks T-14 e T-15.
  - Verificação: build e lint passam; com a API e o `moviestars.db` reais,
    os CAs listados funcionam no navegador.

- [x] **T-20. Layout responsivo** (CA-27)
  - Grade com colunas automáticas; cabeçalho com a busca; paginação que
    quebra linha em telas estreitas.
  - Verificação: em 360 px, 768 px e 1280 px, sem rolagem horizontal e com
    todos os controles utilizáveis.

## Fase 5 — Verificação e fechamento

- [x] **T-21. Roteiro manual no navegador** (CA-1 a CA-24, CA-27)
  - Percorrer cada CA da interface com os dados reais e anotar o resultado
    aqui. O roteiro inclui:
    - primeira, anterior, próxima e última página;
    - busca com e sem acento;
    - busca por "100%";
    - limpar a busca;
    - recarregar a página;
    - voltar e avançar do navegador;
    - `?page=abc` e `?page=99999` na URL;
    - API desligada, seguida de "Tentar novamente";
    - largura de 360 px;
    - clique no cartão.
  - Verificação: todos os itens do roteiro marcados como ok, com os
    problemas encontrados corrigidos antes de marcar.
  - **Resultado (2026-09-26):** o roteiro foi automatizado com Playwright
    (instalado num ambiente temporário no scratchpad, fora das dependências
    do projeto) e rodado contra a API e o `moviestars.db` reais. **42 de 42
    verificações ok.**

    | Área | O que foi conferido | CAs |
    |---|---|---|
    | Listagem | 20 cartões; "95.645 filmes"; "Página 1 de 4.783"; limites desabilitados; última página com 5 filmes | CA-1, CA-3, CA-4 |
    | Ordem | 5 amostras de 100 filmes em ordem normalizada; "À La Recherche…" junto dos "A…" | CA-2 |
    | Cartões | 65 cartões (páginas 1, 300, 2.400 e 4.783) iguais à API: título, ano, estrelas, gêneros ("+N"), diretores ("e mais N"), pôster ou imagem padrão, link | CA-6, CA-7 |
    | Título longo | no máximo 2 linhas, com o texto completo no `title` | CA-8 |
    | Clique | leva a `/filmes/<chave>` ("Página não encontrada" até a 002) | CA-9 |
    | Busca | "ring" com 514 resultados, todos com "ring"; `acao`, `AÇÃO` e `Ação` com o mesmo total; espaços ignorados; "100%" literal; resumo "514 filmes encontrados para "ring"" | CA-10 a CA-13, CA-15 |
    | Debounce | "ring" digitado letra a letra gera uma única requisição | CA-14, RNF-2 |
    | URL | busca volta à página 1; recarregar mantém busca e página; voltar restaura a página e o texto do campo; limpar volta a `/` | CA-16 a CA-19 |
    | URL inválida | `?page=abc` e `?page=0` viram página 1; `?page=99999` mostra "Esta página não existe" com link | CA-20, CA-24 |
    | Estados | carregando (API com atraso); erro com a API bloqueada e "Tentar novamente"; busca sem resultado com "Limpar busca" | CA-21 a CA-23 |
    | Campo | não aceita o 201º caractere | CA-26 |
    | Layout | 360 px (2 colunas), 768 px (4) e 1280 px (6) sem rolagem horizontal; paginação numa linha em 360 px; cabeçalho fixo só a partir de 768 px | CA-27 |

    Problemas encontrados e corrigidos durante a verificação:
    - `?page=10¹⁸` causava erro 500 na API. O serviço agora não consulta
      páginas além da última, e há um teste de regressão.
    - A paginação quebrava em 3 linhas em 360 px. Abaixo de 480 px, os
      botões passaram a mostrar só os símbolos.
    - O cabeçalho fixo ocupava muito espaço em telas estreitas. Ele agora é
      fixo só a partir de 768 px (pedido na revisão da fase 4).

- [x] **T-22. Documentação** (constituição, seção 6)
  - `README.md`: decisões da 001, variável `VITE_API_URL`, passo
    `bun install` (que agora instala `react-router-dom`) e status da 001.
  - `CLAUDE.md`:
    - comando `alembic upgrade head` depois de atualizar o repositório
      (migração 0002);
    - armadilha: ao editar `titulo`, atualizar `titulo_normalizado`;
    - mapa com os arquivos novos.
  - Verificação: seguir o README do zero, num banco novo, deixa o catálogo
    funcionando no navegador.

- [x] **T-23. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .` e `ruff format --check .` passam.
  - Frontend: `bun run build` e `bun run lint` passam.
  - CA-1 a CA-27 conferidos contra os testes, a T-09 e a T-21.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                         |
|-------|-------------------------------|
| CA-1  | T-05, T-08, T-19, T-21        |
| CA-2  | T-01, T-02, T-03, T-05        |
| CA-3  | T-05, T-17, T-19              |
| CA-4  | T-17, T-21                    |
| CA-5  | T-19, T-21                    |
| CA-6  | T-07, T-14, T-15              |
| CA-7  | T-07, T-14                    |
| CA-8  | T-15, T-21                    |
| CA-9  | T-13, T-15, T-21              |
| CA-10 | T-06, T-21                    |
| CA-11 | T-01, T-06, T-21              |
| CA-12 | T-06, T-19                    |
| CA-13 | T-06, T-21                    |
| CA-14 | T-12, T-21                    |
| CA-15 | T-06, T-19                    |
| CA-16 | T-19, T-21                    |
| CA-17 | T-16, T-19                    |
| CA-18 | T-19, T-21                    |
| CA-19 | T-19, T-21                    |
| CA-20 | T-19, T-21                    |
| CA-21 | T-12, T-18, T-19              |
| CA-22 | T-11, T-12, T-18, T-21        |
| CA-23 | T-18, T-19, T-21              |
| CA-24 | T-05, T-18, T-19, T-21        |
| CA-25 | T-08                          |
| CA-26 | T-08, T-16                    |
| CA-27 | T-20, T-21                    |
| RNF-1 | T-09                          |
| RNF-2 | T-12, T-21                    |
