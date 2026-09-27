# 002 — Detalhes do filme e média — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Aprovado — em implementação                             |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos de backend rodam em `backend/` e os de frontend em
`frontend/`. "Build e lint passam" significa que `bun run build` e
`bun run lint` terminam sem erros. Os testes de backend usam as fixtures de
`tests/conftest.py` (feature 001).

## Fase 0 — API de detalhes e avaliações (backend)

- [x] **T-01. `Page[T]` genérico** (DEC-2)
  - Em `schemas.py`, trocar `MoviePage` por `Page(BaseModel, Generic[T])`;
    `list_movies` e a rota `GET /movies` passam a usar `Page[MovieListItem]`.
  - Verificação: os testes da 001 passam sem alteração, inclusive o que
    compara o JSON completo de `GET /movies`; `ruff check .` passa.

- [x] **T-02. `get_movie` e schemas do detalhe** (CA-4, CA-5, CA-7, CA-8, CA-10 a CA-13, CA-15, CA-16)
  - Criar os schemas `MovieFinancials` e `MovieDetail`.
  - Criar `get_movie` com `selectinload` de gêneros, pessoas, produtoras e
    métricas; listas separadas por tipo e em ordem alfabética; média por
    `_ratings_by_movie`/`_to_stars`; `lucro_*` como `None` quando falta
    orçamento ou receita naquela moeda; `financeiro` como `None` sem linha
    no fato; `None` quando o filme não existe.
  - Testes (serviço) em `tests/test_movie_detail_api.py`:
    - todos os campos básicos, gêneros e produtoras em ordem alfabética;
    - pessoas separadas em diretores, roteiristas e elenco, cada lista em
      ordem alfabética;
    - campos ausentes `None` e listas vazias `[]`;
    - financeiro nos 4 cenários: orçamento e receita, só orçamento, nenhum
      e sem linha no fato;
    - chave inexistente devolve `None`.
  - Verificação: `pytest` passa.

- [x] **T-03. Rota `GET /api/v1/movies/{sk_movie_id}`** (CA-1, CA-2, CA-3, CA-16)
  - Rota com `response_model=MovieDetail` e 404 "Filme não encontrado.".
  - Testes pelo `client`:
    - JSON completo de um filme;
    - chave inexistente dá 404 com a mensagem em português;
    - `media_estrelas` e `qtd_avaliacoes` iguais às de `GET /movies` para
      o mesmo filme.
  - Verificação: `pytest` e `ruff check .` passam; `/docs` mostra a rota.

- [x] **T-04. Avaliações: `list_reviews` e `GET /movies/{sk_movie_id}/reviews`** (CA-3, CA-17 a CA-21)
  - Criar o schema `ReviewItem`, com `created_at` em UTC explícito.
  - Criar `list_reviews`, que devolve `None` se o filme não existe; ordem
    `created_at DESC, sk_movie_review_id ASC`; `estrelas = _to_stars(nota)`;
    página além da última sem consulta.
  - Rota com `page` ≥ 1 e `page_size` de 1 a 100 (padrão 10).
  - Testes:
    - avaliação mais nova primeiro;
    - duas com a mesma data, em ordem de chave;
    - nota 9.8 vira 4.9 estrelas;
    - `created_at` termina em `Z`;
    - 13 avaliações dão página 1 com 10 e página 2 com 3, `total` 13 e
      `pages` 2;
    - filme sem avaliações dá `items` vazio e `total` 0;
    - filme inexistente dá 404;
    - `page=0` e `page_size=101` dão 422.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-05. Desempenho com os dados reais** (RNF-1)
  - Medir `GET /movies/{id}` e `/reviews` no `moviestars.db` para:
    - o filme com 88 diretores;
    - o filme com 13 avaliações (páginas 1 e 2);
    - um filme sem avaliações.
  - Anotar os tempos na seção "Riscos" do plan.
  - Verificação: todos abaixo de 1 s.

## Fase 1 — Base do frontend

- [x] **T-06. Pasta `utils/` e formatações** (CA-4, CA-11, CA-18, DEC-8)
  - Constituição:
    - acrescentar `utils/` à tabela da seção 5.3;
    - registrar a alteração na seção 8.
  - Criar `src/utils/format.ts` com `formatDate`, `formatDateTime`,
    `formatDuration` e `formatMoney`.
  - Verificação: build e lint passam. Um script temporário rodado com
    `bun` (fora do projeto) confere:
    - `formatDate("2017-02-01")` = `"01/02/2017"`;
    - `formatDuration(102)` = `"1 h 42 min"`, `58` = `"58 min"`, `120` =
      `"2 h"`, e `0` e `null` = `"Duração não informada"`;
    - `formatMoney(-7500000, "BRL")` mostra o sinal negativo e
      `"R$ 7.500.000,00"`, e o mesmo valor em `"USD"` mostra `"US$"`;
    - `formatDateTime("2026-09-27T01:30:00Z")` mostra 26/09/2026 no fuso
      de São Paulo.

- [x] **T-07. Tipos e chamadas à API**
  - `types/movie.ts`: `MovieDetail`, `MovieFinancials`, `Review`.
  - `api/movies.ts`: `getMovie` e `listMovieReviews`.
  - Verificação: build e lint passam, sem `any`.

- [x] **T-08. Hooks `useMovie` e `useMovieReviews`** (CA-3, CA-19, CA-22, CA-26, CA-27)
  - `useMovie(id)`:
    - estados `loading`, `error`, `not-found` (resposta 404) e `success`;
    - `retry()`;
    - cancela a requisição ao trocar de filme.
  - `useMovieReviews(id)`:
    - primeira página ao abrir;
    - `loadMore()` acrescenta a próxima;
    - `loadingMore` e `loadMoreError`, sem perder os itens já exibidos;
    - `retryLoadMore()`;
    - `hasMore`.
  - Verificação: build e lint passam, sem avisos das regras de hooks.

- [x] **T-09. `Poster`, `StarRating` e estado no link do cartão** (CA-4, CA-18, CA-23, DEC-9, DEC-10)
  - Extrair `Poster` do `MovieCard`, que passa a usá-lo.
  - `StarRating` com `count` opcional.
  - O `Link` do `MovieCard` passa `state={{ catalogSearch }}` com a busca e
    a página atuais.
  - Verificação: build e lint passam; o roteiro da 001
    (`check_catalog.py`) continua 34/34.

## Fase 2 — Componentes da página

- [ ] **T-10. `NameList`** (CA-7 a CA-10)
  - Título, até 10 nomes, "Mostrar todos (N)" / "Mostrar menos" e "Não
    informado".
  - Verificação: build e lint passam. Na página de detalhes (T-13), o filme
    com 88 diretores mostra 10 nomes e o botão.

- [ ] **T-11. `FinancialTable`** (CA-11 a CA-14)
  - Linhas Orçamento, Receita e Lucro; colunas Real e Dólar. Mostra "Não
    informado", "Não calculado" e o lucro negativo destacado como prejuízo.
  - Verificação: build e lint passam; conferido na T-15 com filmes reais
    nos três cenários.

- [ ] **T-12. `ReviewList`** (CA-17 a CA-22)
  - Título "Avaliações (N)" e itens com nome, estrelas, comentário e data.
  - Botão "Mostrar mais avaliações" enquanto `hasMore`.
  - Erro de "mostrar mais" com "Tentar de novo".
  - Lista vazia com "Este filme ainda não tem avaliações.".
  - Verificação: build e lint passam; conferido na T-15.

## Fase 3 — Página de detalhes

- [ ] **T-13. `MovieDetailPage` e rota** (CA-1 a CA-6, CA-15, CA-23, CA-25 a CA-27)
  - Rota `/filmes/:skMovieId` em `App.tsx`.
  - A página tem:
    - a faixa de fundo, que some se não houver imagem ou se ela falhar;
    - o pôster, o título, o ano, a data, a duração, o status, os gêneros,
      a média e a sinopse, com os textos de ausência do CA-5;
    - as seções de equipe, produtoras, financeiro e avaliações;
    - o link "Voltar ao catálogo" com o `catalogSearch`;
    - o título da aba;
    - os estados carregando, erro com "Tentar novamente" e "Filme não
      encontrado".
  - Verificação: build e lint passam; com a API real, um filme abre
    completo, e uma chave inexistente mostra "Filme não encontrado".

- [ ] **T-14. Layout responsivo** (CA-28)
  - Duas colunas (pôster e informações) a partir de 640 px e uma coluna
    abaixo; a tabela financeira cabe em 360 px.
  - Verificação: em 360 px, 768 px e 1280 px, sem rolagem horizontal.

## Fase 4 — Verificação e fechamento

- [ ] **T-15. Roteiro no navegador** (CA-1 a CA-28)
  - Script Playwright (no scratchpad) contra a API e o `moviestars.db`
    reais, cobrindo os itens da seção "Testes" do plan.
  - Anotar os resultados aqui.
  - Verificação: todos os itens ok, com os problemas encontrados corrigidos
    antes de marcar.

- [ ] **T-16. Documentação** (constituição, seção 6)
  - `README.md`: decisões da 002 e status.
  - `CLAUDE.md`:
    - mapa com os arquivos novos (`utils/`, hooks e componentes);
    - armadilha de datas: `data_lancamento` sem `new Date`, e `created_at`
      em UTC.
  - Verificação: os links e comandos citados existem.

- [ ] **T-17. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .` e `ruff format --check .` passam.
  - Frontend: `bun run build` e `bun run lint` passam.
  - CA-1 a CA-28 conferidos contra os testes, a T-05 e a T-15.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                         |
|-------|-------------------------------|
| CA-1  | T-03, T-13, T-15              |
| CA-2  | T-03, T-13, T-15              |
| CA-3  | T-02, T-03, T-04, T-08, T-13  |
| CA-4  | T-02, T-06, T-09, T-13        |
| CA-5  | T-02, T-13                    |
| CA-6  | T-13, T-15                    |
| CA-7  | T-02, T-10                    |
| CA-8  | T-02, T-10                    |
| CA-9  | T-10, T-15                    |
| CA-10 | T-02, T-10                    |
| CA-11 | T-02, T-06, T-11              |
| CA-12 | T-02, T-11                    |
| CA-13 | T-02, T-11                    |
| CA-14 | T-06, T-11                    |
| CA-15 | T-02, T-13                    |
| CA-16 | T-02, T-03, T-15              |
| CA-17 | T-04, T-12                    |
| CA-18 | T-04, T-06, T-09, T-12        |
| CA-19 | T-04, T-08, T-12, T-15        |
| CA-20 | T-04, T-12                    |
| CA-21 | T-04, T-12                    |
| CA-22 | T-08, T-12, T-15              |
| CA-23 | T-09, T-13, T-15              |
| CA-24 | T-15                          |
| CA-25 | T-13, T-15                    |
| CA-26 | T-08, T-13                    |
| CA-27 | T-08, T-13, T-15              |
| CA-28 | T-14, T-15                    |
| RNF-1 | T-05                          |
