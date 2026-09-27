# 002 — Detalhes do filme e média — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Aprovado                                              |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 4.1, 4.2, 4.4, 5, 6); plan da 001 (DEC-7) |

## Visão geral

```text
/filmes/:skMovieId  (MovieDetailPage)
   │
   ├── GET /api/v1/movies/{sk_movie_id}                 → dados do filme + média (1 requisição)
   └── GET /api/v1/movies/{sk_movie_id}/reviews?page=N  → 10 avaliações por vez ("Mostrar mais")
```

As duas requisições saem em paralelo quando a página abre. "Mostrar mais
avaliações" pede a próxima página da segunda e acrescenta os itens à lista.

## Backend

### Página genérica (DEC-2)

Com as avaliações, passam a existir dois endpoints paginados. Como previsto
na DEC-7 da 001, `MoviePage` vira um schema genérico em
`app/movies/schemas.py`:

```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

`GET /movies` passa a declarar `response_model=Page[MovieListItem]`. O JSON
não muda, e os testes da 001 continuam valendo.

### `GET /api/v1/movies/{sk_movie_id}`

Resposta `200` (`MovieDetail`; valores ilustrativos):

```json
{
  "sk_movie_id": "b5c3…",
  "titulo": "Rings",
  "ano_lancamento": 2017,
  "data_lancamento": "2017-02-01",
  "duracao_minutos": 102,
  "status_filme": "Lançado",
  "sinopse": "Julia becomes worried…",
  "url_poster": "https://image.tmdb.org/t/p/w500/….jpg",
  "url_backdrop": "https://image.tmdb.org/t/p/w1280/….jpg",
  "generos": ["Horror"],
  "diretores": ["F. Javier Gutiérrez"],
  "roteiristas": ["Akiva Goldsman", "David Loucka"],
  "elenco": ["Alex Roe", "Matilda Lutz"],
  "produtoras": ["Paramount Pictures"],
  "financeiro": {
    "orcamento_brl": 78682500.0, "receita_brl": 261480485.1, "lucro_brl": 182797985.1,
    "orcamento_usd": 25000000.0, "receita_usd": 83080890.0, "lucro_usd": 58080890.0
  },
  "media_estrelas": 0.5,
  "qtd_avaliacoes": 1
}
```

- `404` com `{"detail": "Filme não encontrado."}` quando a chave não existe
  (CA-3).
- `generos`, `diretores`, `roteiristas`, `elenco` e `produtoras` vêm em
  ordem alfabética e completos. O limite de 10 com "Mostrar todos" fica na
  interface (CA-9).
- `financeiro`:
  - valores ausentes são `null`;
  - `lucro_*` é `null` quando falta orçamento **ou** receita naquela moeda
    (D-5 da spec, DEC-4);
  - o objeto é `null` se o filme não tiver linha em
    `fact_movies_performance`, o que hoje não acontece, mas pode acontecer
    com filmes criados na 003.
- `media_estrelas` e `qtd_avaliacoes` usam as mesmas funções do catálogo
  (`_ratings_by_movie` e `_to_stars`), o que garante o CA-16.

### `GET /api/v1/movies/{sk_movie_id}/reviews`

| Parâmetro   | Padrão | Validação (422)   |
|-------------|--------|-------------------|
| `page`      | 1      | ≥ 1               |
| `page_size` | 10     | entre 1 e 100     |

Resposta `200` (`Page[ReviewItem]`; valores ilustrativos):

```json
{
  "items": [
    {
      "sk_movie_review_id": "a960…",
      "nome": "Henrique Carvalho",
      "estrelas": 4.9,
      "comentario": "Adorei cada minuto, uma experiência inesquecível.",
      "created_at": "2026-09-26T20:56:13Z"
    }
  ],
  "total": 13, "page": 1, "page_size": 10, "pages": 2
}
```

- `404` quando o filme não existe, para não confundir com um filme sem
  avaliações.
- Ordem: `created_at DESC, sk_movie_review_id ASC` (CA-17). O desempate
  pela chave mantém fixa a ordem das importadas, que têm todas a mesma data.
- `estrelas = _to_stars(nota)`: a mesma conversão e o mesmo arredondamento
  da média (constituição, seção 4.1).
- `created_at` sai com fuso UTC (`…Z`), e a interface converte para o
  horário local (DEC-5).
- Página além da última: `items: []`, como no catálogo, e sem consultar a
  página (a mesma proteção contra páginas enormes da 001).

### Schemas novos (`app/movies/schemas.py`)

| Schema             | Campos                                                   |
|--------------------|----------------------------------------------------------|
| `Page[T]`          | substitui `MoviePage` (DEC-2)                            |
| `MovieFinancials`  | `orcamento_brl`, `receita_brl`, `lucro_brl`, `orcamento_usd`, `receita_usd`, `lucro_usd` (todos `float \| None`) |
| `MovieDetail`      | campos do exemplo acima; `data_lancamento: date \| None`; `financeiro: MovieFinancials \| None` |
| `ReviewItem`       | `sk_movie_review_id`, `nome`, `estrelas`, `comentario`, `created_at: datetime` |

### Consultas (`app/movies/service.py`)

`get_movie(db, sk_movie_id) -> MovieDetail | None`:

```python
select(DimMovie).where(DimMovie.sk_movie_id == sk_movie_id).options(
    selectinload(DimMovie.genres),
    selectinload(DimMovie.people),
    selectinload(DimMovie.companies),
    selectinload(DimMovie.performance),
)
```

As pessoas são separadas por `tipo_pessoa` em Python, e a média vem de
`_ratings_by_movie(db, [sk_movie_id])`. São 6 consultas pequenas por chave
primária, sem N+1. Se o filme não existir, a função devolve `None` e a rota
responde `404`.

`list_reviews(db, sk_movie_id, page, page_size) -> Page[ReviewItem] | None`:

1. confere se o filme existe (`db.get(DimMovie, …)`); se não, devolve
   `None` e a rota responde `404`;
2. `COUNT(*)` das avaliações do filme;
3. se `offset < total`: seleciona as avaliações na ordem acima, com
   `offset` e `limit`. O índice `ix_movie_reviews_sk_movie_id` já existe.

### Rotas (`app/movies/router.py`)

| Rota                                  | `response_model`     | Erros       |
|---------------------------------------|----------------------|-------------|
| `GET /movies/{sk_movie_id}`           | `MovieDetail`        | 404         |
| `GET /movies/{sk_movie_id}/reviews`   | `Page[ReviewItem]`   | 404, 422    |

A mensagem de erro é `HTTPException(404, "Filme não encontrado.")`, em
português (constituição, seção 5.2).

## Frontend

### Rota

`App.tsx` ganha `/filmes/:skMovieId` → `MovieDetailPage`. A rota coringa
`NotFoundPage` continua para os outros endereços.

### Arquivos

| Arquivo                                | Responsabilidade                                          | CAs |
|----------------------------------------|-----------------------------------------------------------|-----|
| `src/types/movie.ts`                   | `MovieDetail`, `MovieFinancials`, `Review`                | —   |
| `src/api/movies.ts`                    | `getMovie(id, signal)` e `listMovieReviews(id, { page, pageSize }, signal)` | — |
| `src/utils/format.ts` (novo, DEC-8)    | `formatDate` ("01/02/2017", sem deslocar fuso), `formatDateTime` (UTC → data local), `formatDuration` ("1 h 42 min"), `formatMoney` (Intl pt-BR: "R$ 78.682.500,00", "US$ 25.000.000,00") | CA-4, CA-11, CA-18 |
| `src/hooks/useMovie.ts`                | Estado `loading`, `error`, `not-found` ou `success`, e `retry()` | CA-3, CA-26, CA-27 |
| `src/hooks/useMovieReviews.ts`         | Primeira página ao abrir; `loadMore()` acrescenta a próxima; estados `loadingMore` e `loadMoreError`; `retryLoadMore()` | CA-19, CA-22 |
| `src/components/Poster.tsx` (DEC-9)    | Imagem com troca para a padrão em `onError`, extraída do `MovieCard`, que passa a usá-la | CA-4 |
| `src/components/StarRating.tsx`        | `count` passa a ser opcional (a avaliação individual não mostra quantidade) | CA-15, CA-18 |
| `src/components/NameList.tsx`          | Título, até 10 nomes, "Mostrar todos (N)" / "Mostrar menos", "Não informado" | CA-7 a CA-10 |
| `src/components/FinancialTable.tsx`    | Tabela Orçamento/Receita/Lucro × Real/Dólar; "Não informado", "Não calculado"; prejuízo destacado | CA-11 a CA-14 |
| `src/components/ReviewList.tsx`        | Título "Avaliações (N)", itens (nome, estrelas, comentário, data), "Mostrar mais avaliações", erro com "Tentar de novo", lista vazia | CA-17 a CA-22 |
| `src/pages/MovieDetailPage.tsx`        | Faixa de fundo, pôster e informações, média, seções, voltar, título da aba, estados | CA-1 a CA-6, CA-15, CA-23 a CA-28 |
| `.css` de cada componente/página novo  | Layout de duas colunas; uma coluna abaixo de 640 px       | CA-28 |

### Voltar ao catálogo (CA-23, CA-24, DEC-10)

- O `Link` do `MovieCard` passa `state={{ catalogSearch: location.search }}`
  (ex.: `?search=ring&page=3`).
- A página de detalhes lê esse estado. Se ele existir, "Voltar ao catálogo"
  aponta para `/` + `catalogSearch`; se não (endereço aberto direto), aponta
  para `/`.
- O botão voltar do navegador já funciona, porque o catálogo guarda a página
  e a busca na URL (spec 001).

### Detalhes de formatação

- **Data de lançamento:** vem como `"2017-02-01"` e é formatada dividindo o
  texto. `new Date("2017-02-01")` seria meia-noite em UTC, e no Brasil
  (UTC−3) viraria 31/01/2017.
- **Data da avaliação:** vem em UTC (`…Z`) e é exibida no fuso local com
  `toLocaleDateString("pt-BR")`.
- **Duração:** 0 ou ausente mostra "Duração não informada"; abaixo de 60,
  "58 min"; a partir de 60, "1 h 42 min" (ou "2 h" em hora exata).
- **Título da aba:** `"<título> — MovieStars"` enquanto a página está
  aberta; volta a `"MovieStars"` ao sair (CA-25).

## Arquivos

| Arquivo                                   | Ação    |
|-------------------------------------------|---------|
| `backend/app/movies/schemas.py`           | Alterar (`Page[T]`, `MovieFinancials`, `MovieDetail`, `ReviewItem`) |
| `backend/app/movies/service.py`           | Alterar (`get_movie`, `list_reviews`; `list_movies` devolve `Page[MovieListItem]`) |
| `backend/app/movies/router.py`            | Alterar (2 rotas) |
| `backend/tests/test_movie_detail_api.py`  | Criar   |
| `frontend/src/App.tsx`                    | Alterar (rota) |
| `frontend/src/types/movie.ts`, `src/api/movies.ts` | Alterar |
| `frontend/src/utils/format.ts`            | Criar   |
| `frontend/src/hooks/useMovie.ts`, `useMovieReviews.ts` | Criar |
| `frontend/src/components/Poster.tsx`, `NameList.tsx`, `FinancialTable.tsx`, `ReviewList.tsx` (+ `.css`) | Criar |
| `frontend/src/components/MovieCard.tsx`, `StarRating.tsx` | Alterar |
| `frontend/src/pages/MovieDetailPage.tsx` (+ `.css`) | Criar |
| `specs/constitution.md`                   | Alterar (pasta `utils/` na seção 5.3 e registro na seção 8, DEC-8) |
| `README.md`, `CLAUDE.md`                  | Alterar (decisões, status, mapa do código) |

## Testes

### Backend (`tests/test_movie_detail_api.py`, com as fixtures da 001)

| Teste                                                                 | CAs          |
|-----------------------------------------------------------------------|--------------|
| Detalhe completo: campos básicos, gêneros e produtoras em ordem alfabética | CA-4, CA-8 |
| Pessoas separadas em diretores, roteiristas e elenco, cada lista em ordem alfabética | CA-7 |
| Campos ausentes vêm `null`; listas vazias vêm `[]`                    | CA-5, CA-10  |
| Financeiro: com orçamento e receita (lucro presente); só orçamento (lucro `null`); nenhum (tudo `null`); sem linha no fato (`financeiro: null`) | CA-11 a CA-13 |
| Média e quantidade iguais às do `GET /movies` para o mesmo filme      | CA-15, CA-16 |
| Filme inexistente → 404 com mensagem em português                     | CA-3         |
| Avaliações: mais recentes primeiro; empate de data em ordem fixa pela chave | CA-17  |
| `estrelas` = nota ÷ 2 com 1 casa; `created_at` termina em `Z`         | CA-18        |
| 13 avaliações: página 1 com 10, página 2 com 3, `total` 13, `pages` 2 | CA-19, CA-20 |
| Filme sem avaliações: `items` vazio, `total` 0                        | CA-21        |
| Avaliações de filme inexistente → 404; `page=0` e `page_size=101` → 422 | CA-3       |
| `GET /movies` continua com o mesmo JSON depois da troca para `Page[T]` | —           |

### Frontend

`build` e `lint`, e um roteiro no navegador com o Playwright do scratchpad,
como na 001, contra os dados reais:
- clique no cartão;
- recarregar a página;
- chave inexistente;
- filme com imagem de fundo e filme sem;
- filme com mais de 10 diretores ("Mostrar todos");
- filme com orçamento e receita, e filme sem;
- filme com 13 avaliações ("Mostrar mais");
- falha simulada ao carregar mais avaliações;
- voltar ao catálogo com busca e página preservadas;
- título da aba;
- 360 px.

### Com os dados reais

- Tempo de resposta (RNF-1) do detalhe e das avaliações do filme com mais
  pessoas (88 diretores) e do filme com 13 avaliações.

## Decisões

- **DEC-1. Dois endpoints: detalhe e avaliações.** As avaliações têm
  paginação própria ("Mostrar mais"), e o mesmo endpoint serve à feature 004
  para recarregar a lista depois de adicionar uma avaliação.
  *Descartado:* incluir a primeira página de avaliações dentro do detalhe,
  o que criaria dois caminhos para o mesmo dado.
- **DEC-2. `Page[T]` genérico no lugar de `MoviePage`.** É o segundo
  endpoint paginado, o momento previsto na DEC-7 da 001. O JSON do catálogo
  não muda.
  *Descartado:* criar um `ReviewPage` separado, que duplicaria o formato.
- **DEC-3. Valores financeiros como `float` no JSON.** Com no máximo 2 casas
  e até cerca de 12 bilhões, o `float` representa os valores sem perda
  visível, e o frontend recebe números prontos para formatar.
  *Descartado:* `Decimal`, que o Pydantic serializa como texto e obrigaria a
  converter no frontend.
- **DEC-4. A regra do lucro (D-5 da spec) fica no serviço.** É testada no
  pytest, e a interface só exibe "Não calculado" quando recebe `null`.
  *Descartado:* aplicar a regra no frontend, sem teste automatizado.
- **DEC-5. `created_at` em UTC explícito (`Z`), convertido para o horário
  local na interface.** O SQLite grava `CURRENT_TIMESTAMP` em UTC e sem
  fuso. A carga, rodada às 17:56 no horário local, ficou com 20:56. Sem a
  conversão, avaliações feitas à noite mostrariam o dia seguinte.
  *Descartado:* exibir o valor como vem.
- **DEC-6. As estrelas da avaliação usam o mesmo `_to_stars` da média.** A
  conversão e o arredondamento ficam num lugar só (constituição, seção 4.1).
- **DEC-7. Ordem das avaliações: `created_at DESC`, desempate por
  `sk_movie_review_id`.** O CA-17 pede ordem estável entre avaliações com a
  mesma data, e as 43.666 importadas têm todas a mesma.
- **DEC-8. Pasta nova `src/utils/` para formatações** (data, data e hora,
  duração, dinheiro), usadas por vários componentes. A constituição (seção
  5.3) lista as pastas do frontend, então a tabela e o registro de
  alterações da seção 8 serão atualizados.
  *Descartado:* repetir as funções em cada componente.
- **DEC-9. Componente `Poster` extraído do `MovieCard`.** O catálogo e os
  detalhes usam a mesma troca para a imagem padrão.
  *Descartado:* duplicar a lógica.
- **DEC-10. "Voltar ao catálogo" usa o estado da navegação do React
  Router.** Funciona também quando a página é aberta direto (volta para
  `/`).
  *Descartado:* `history.back()`, que tiraria o usuário do site se ele
  tivesse aberto o link direto. *Descartado:* guardar no `sessionStorage`,
  que é mais código para o mesmo resultado.
- **DEC-11. Um componente `NameList` para as quatro listas** (Direção,
  Roteiro, Elenco, Produtoras): a mesma regra de 10 nomes e "Mostrar todos"
  num lugar só.
- **DEC-12. "Mostrar mais" acumula as páginas no estado da tela** e pede a
  próxima página por número. É a paginação por deslocamento que o backend já
  usa. A repetição rara, quando uma avaliação é criada durante a navegação,
  foi aceita na spec.
  *Descartado:* paginação por cursor, mais complexa, para um caso que a spec
  aceitou.

## Riscos

- **RNF-1: confirmado na T-05 (2026-09-26).** Pior tempo em 5 execuções
  com o `moviestars.db` real:

  | Consulta                                   | Tempo  |
  |--------------------------------------------|--------|
  | detalhe do filme com 88 diretores          | 51 ms  |
  | detalhe do filme com 13 avaliações         | 4 ms   |
  | avaliações p.1 e p.2 (13 avaliações)       | 4 ms e 2 ms |
  | detalhe e avaliações de filme sem avaliações | 5 ms e 2 ms |

- **Filmes criados pela 003 sem métricas:** `financeiro` pode ser `null`, e
  a interface mostra a seção com "Não informado". Coberto por teste.
- **Imagens externas:** a imagem de fundo `w1280` pesa mais que o pôster. É
  uma imagem só, no topo; aceitável.
