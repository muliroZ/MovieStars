# 100 — Filtros e ordenação do catálogo — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Aprovado                                              |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 4.2, 4.6, 5); plans da 001 (DEC-1), 003 (DEC-3, DEC-8) e 004 |

## Visão geral

```text
CatalogPage ── URL: ?search=&page=&genre=&genre_mode=&year_min=&year_max=&status=&reviews=&min_stars=&sort=&reverse=
 ├─ SearchBar (001)
 ├─ CatalogToolbar ── [Filtros (N)]  [Ordenar ▾] [Inverter]
 ├─ FilterPanel (recolhível) ── GenrePicker (003) + Qualquer um/Todos · Ano de/até · Status · Avaliações · StarInput (004)
 └─ grade + paginação (001)
          │ GET /api/v1/movies?...mesmos parâmetros
          ▼
 list_movies(db, page, page_size, search, filters)
   condições em dim_movies + subconsulta de gêneros
   + agregado de avaliações (AVG/COUNT) só quando um filtro ou a ordenação precisa dele
```

## Backend

### Parâmetros de `GET /api/v1/movies` (DEC-1, DEC-2)

Os parâmetros novos se juntam a `page`, `page_size` e `search` num modelo de
consulta, `CatalogQuery`, em `app/movies/schemas.py`. O FastAPI lê o modelo
direto da URL com `Annotated[CatalogQuery, Query()]`.

| Parâmetro    | Tipo                                    | Padrão   | Validação (422, em português)                          | CAs  |
|--------------|-----------------------------------------|----------|--------------------------------------------------------|------|
| `genre`      | `list[str]` (repetível)                 | `[]`     | nenhuma: um nome que não existe só não encontra filmes (DEC-9) | CA-3, CA-4 |
| `genre_mode` | `Literal["any", "all"]`                 | `"any"`  | "Valor inválido."                                      | CA-4 |
| `year_min`, `year_max` | `int \| None`                 | `None`   | de 1888 até o ano atual + 10 ("Deve estar entre 1888 e <ano>."); `year_min` > `year_max` → "O ano inicial deve ser menor ou igual ao final." no campo `year_max` | CA-5 |
| `status`     | `list[MovieStatus]` (repetível)         | `[]`     | "Valor inválido."                                      | CA-6 |
| `reviews`    | `Literal["all", "with", "without"]`     | `"all"`  | "Valor inválido."                                      | CA-7 |
| `min_stars`  | `int \| None`, de 1 a 5                 | `None`   | "Deve ser no mínimo 1." / "Deve ser no máximo 5."      | CA-8 |
| `sort`       | `Literal["title", "year", "rating", "reviews"]` | `"title"` | "Valor inválido."                               | CA-13 |
| `reverse`    | `bool`                                  | `False`  | —                                                      | CA-14 |

- O formato da resposta não muda (`Page[MovieListItem]`).
- A combinação `reviews=without` com `min_stars` não é um erro: ela devolve
  uma lista vazia. A interface já impede essa combinação (CA-9).
- Os validadores próprios (faixa de ano e ano inicial maior que o final)
  lançam `ValueError` com a mensagem em português. O tratador da 003 só tira
  o prefixo do Pydantic (CA-21).

### Serviço (`app/movies/service.py`)

`list_movies(db, page, page_size, search="", filters=None)` (DEC-3):
- `filters: CatalogFilters | None`, um schema com os campos acima, sem
  `page`, `page_size` e `search`.
- Sem `filters`, o comportamento é exatamente o da 001. As 17 chamadas nos
  testes da 001 continuam iguais.

A consulta é montada em funções pequenas:

| Função                                  | O que devolve                                                        |
|-----------------------------------------|----------------------------------------------------------------------|
| `_review_stats()`                       | Subconsulta `SELECT sk_movie_id, AVG(nota) AS media, COUNT(*) AS qtd FROM movie_reviews GROUP BY sk_movie_id` |
| `_needs_stats(filters)`                 | `True` com `reviews=with`, `min_stars` ou `sort` em `rating`/`reviews` (DEC-4) |
| `_filter_conditions(filters, term, stats)` | Lista de condições para o `WHERE` (tabela abaixo)                 |
| `_order_by(filters, stats)`             | Lista do `ORDER BY` (tabela abaixo)                                  |

Condições (`WHERE`):

| Filtro                     | Condição                                                               |
|----------------------------|------------------------------------------------------------------------|
| busca (001)                | `titulo_normalizado LIKE %termo%` (como hoje)                          |
| `genre` com `any`          | `sk_movie_id IN (SELECT b.sk_movie_id FROM bridge_movie_genre b JOIN dim_genres g … WHERE g.nome_genero IN (…))` |
| `genre` com `all`          | a mesma subconsulta com `GROUP BY b.sk_movie_id HAVING COUNT(*) = <nº de gêneros distintos>` |
| `year_min` / `year_max`    | `ano_lancamento >= …` / `<= …`                                         |
| `status`                   | `status_filme IN (…)`                                                  |
| `reviews=with`             | `stats.qtd IS NOT NULL` (com o `LEFT JOIN` do agregado)                |
| `reviews=without`          | `NOT EXISTS (SELECT 1 FROM movie_reviews r WHERE r.sk_movie_id = dim_movies.sk_movie_id)` (DEC-5) |
| `min_stars=N`              | `ROUND(stats.media / 2, 1) >= N` (DEC-6)                               |

Ordenação (`ORDER BY`, DEC-7):

| `sort`    | Direção padrão (`reverse=false`)  | Com `reverse=true`       | Desempate               |
|-----------|-----------------------------------|--------------------------|-------------------------|
| `title`   | `titulo_normalizado ASC`          | `titulo_normalizado DESC`| `ano_lancamento`, `sk_movie_id` |
| `year`    | `ano_lancamento DESC NULLS LAST`  | `ASC NULLS LAST`         | `titulo_normalizado`, `ano_lancamento`, `sk_movie_id` |
| `rating`  | `stats.media DESC NULLS LAST`     | `ASC NULLS LAST`         | idem                    |
| `reviews` | `COALESCE(stats.qtd, 0) DESC`     | `ASC`                    | idem                    |

- **Total:** `COUNT(*)` com as mesmas condições. O agregado só entra na
  contagem quando um **filtro** precisa dele (`reviews=with`, `min_stars`);
  ordenar sozinho não custa nada na contagem.
- **Página:** a mesma lógica da 001 (`offset < total`, senão lista vazia),
  mais os `selectinload` e o `_ratings_by_movie` dos 20 filmes da página,
  sem mudança.

### Migração `0004_indices_filtros.py` (DEC-8)

1. Cria `ix_movie_reviews_movie_nota` em `movie_reviews (sk_movie_id, nota)`,
   o índice cobridor da abordagem A.
2. Remove `ix_movie_reviews_sk_movie_id`: o índice novo começa pela mesma
   coluna e atende às mesmas consultas (a lista de avaliações da 002 e o
   `DELETE` em cascata da 003).
3. Cria `ix_bridge_movie_genre_genero` em `bridge_movie_genre (sk_genre_id,
   sk_movie_id)`. A chave primária começa por `sk_movie_id` e não serve para
   buscar filmes por gênero. Na medição em memória, o "qualquer um" de três
   gêneros caiu de 104 para 67 ms, e o "todos" de dois gêneros de 21 para
   0,3 ms.
4. O `downgrade` desfaz os três passos.

O `models.py` acompanha:
- `MovieReview.sk_movie_id` perde o `index=True`;
- `MovieReview.__table_args__` ganha o índice novo;
- a tabela `bridge_movie_genre` ganha o seu índice.

Assim o `alembic check` continua sem diferenças.

### Arquivos do backend

| Arquivo                                          | Ação                                    |
|--------------------------------------------------|-----------------------------------------|
| `app/movies/schemas.py`                          | `CatalogFilters`, `CatalogQuery`        |
| `app/movies/service.py`                          | `list_movies` com `filters`; funções de apoio |
| `app/movies/router.py`                           | `GET /movies` com `Annotated[CatalogQuery, Query()]` |
| `app/movies/models.py`                           | índices                                 |
| `migrations/versions/0004_indices_filtros.py`    | criar                                   |
| `tests/test_catalog_filters_api.py`              | criar                                   |

## Frontend

### Estado dos filtros (`src/utils/catalogFilters.ts`, novo)

```ts
interface CatalogFilters {
  genres: string[]; genreMode: 'any' | 'all'
  yearMin: number | null; yearMax: number | null
  status: MovieStatus[]; reviews: 'all' | 'with' | 'without'
  minStars: number | null
  sort: 'title' | 'year' | 'rating' | 'reviews'; reverse: boolean
}
```

| Função                                   | O que faz                                                    | CAs |
|------------------------------------------|--------------------------------------------------------------|-----|
| `parseFilters(searchParams)`             | Lê da URL e ignora valores inválidos (status fora da lista, ano não numérico ou fora da faixa, estrelas fora de 1 a 5, sort desconhecido) | CA-20 |
| `writeFilters(params, filters)`          | Grava na URL sem os valores padrão (`/` continua limpo)      | CA-19 |
| `activeFilterCount(filters)`             | Quantos filtros estão ativos, para "Filtros (N)" e "K filtros ativos"; a ordenação não conta | CA-1, CA-17 |
| `filtersToApiParams(filters)`            | Parâmetros da API                                            | —   |
| `validateYearRange(de, até)`             | Erros dos campos de ano, com as mesmas mensagens da API      | CA-5 |
| `DEFAULT_FILTERS`, `SORT_OPTIONS`        | Padrões e rótulos da ordenação (D-11 da spec)                | CA-13 |

- **Gêneros inválidos na URL (D-14):** a lista de gêneros vem do hook
  `useGenres` (abaixo). Quando ela chega, o `CatalogPage` tira da URL os
  nomes que não existem, com `replace`, sem criar uma entrada no histórico.

### Mudanças e arquivos

| Arquivo                                  | Mudança                                                      | CAs |
|------------------------------------------|--------------------------------------------------------------|-----|
| `src/api/client.ts`                      | `QueryParams` aceita listas (repete a chave) e booleanos (DEC-10) | — |
| `src/api/movies.ts`                      | `listMovies` recebe os filtros                               | —   |
| `src/hooks/useGenres.ts` (novo)          | Busca `GET /genres` uma vez (carregando, erro, dados). O `GenrePicker` da 003 passa a usá-lo, com o mesmo comportamento (DEC-11) | CA-3, CA-20 |
| `src/hooks/useMovies.ts`                 | Recebe os filtros; a chave da requisição inclui os filtros serializados | CA-11 |
| `src/components/CatalogToolbar.tsx` (novo) | Botão "Filtros (N)" com `aria-expanded`; `<select>` de ordenação; botão "Inverter" com `aria-pressed` | CA-1, CA-2, CA-13, CA-14 |
| `src/components/FilterPanel.tsx` (novo)  | Os filtros, organizados assim: Gêneros (`GenrePicker` + botões de opção "Qualquer um"/"Todos"); Ano (dois campos com estado próprio, espera de 400 ms, erro de faixa; a URL só muda com valores válidos, DEC-12); Status (etiquetas de seleção múltipla); Avaliações (três botões de opção); Mínimo de estrelas (`StarInput` + "Qualquer nota", desabilitados com "Sem avaliação"); "Limpar filtros" | CA-3 a CA-12 |
| `src/components/StarInput.tsx`           | Nova propriedade `disabled`                                  | CA-9 |
| `src/pages/CatalogPage.tsx`              | Lê os filtros da URL; `setFilters` grava com `push` e volta à página 1; painel aberto ou fechado em estado local; resumo com " · K filtros ativos"; vazio com filtros: mensagem do CA-18 e "Limpar filtros" | CA-11, CA-12, CA-17 a CA-19 |
| `.css` dos componentes novos             | Painel em uma coluna abaixo de 768 px e em duas a partir daí; barra que quebra linha | CA-23 |

### Comportamentos

- **"Sem avaliação" (CA-9):** grava `reviews=without` e `minStars=null` na
  mesma mudança.
- **"Limpar filtros" (CA-12):** volta tudo ao `DEFAULT_FILTERS`, exceto
  `sort` e `reverse`, e mantém a busca.
- **Trocar de campo de ordenação (CA-14):** mantém o `reverse`.
- **Histórico (CA-19):** cada mudança cria uma entrada. Os campos de ano só
  criam a entrada depois da espera. Quando o voltar do navegador muda a URL,
  os campos de ano acompanham (o mesmo padrão da busca na 001).

## Testes

### Backend (`tests/test_catalog_filters_api.py`)

| Teste                                                                   | CAs          |
|-------------------------------------------------------------------------|--------------|
| `genre` com `any` e `all`; gênero inexistente (vazio com `all`; ignorado com `any` entre outros); filme sem gênero nunca aparece | CA-3, CA-4 |
| Ano: só `year_min`, só `year_max`, os dois (inclusivos)                 | CA-5         |
| `status` com dois valores                                               | CA-6         |
| `reviews=with` e `without`                                              | CA-7         |
| `min_stars`: média 3,96 (exibida 4,0) entra em 4; 3,94 não; sem avaliação nunca | CA-8   |
| Combinação de filtros e busca; `total` e `pages` corretos               | CA-10        |
| Cada `sort` nas duas direções; sem ano e sem avaliação no fim nas duas; quantidade 0 segue a direção; desempate pelo título; páginas sem repetição | CA-13 a CA-16 |
| 422 em português: `year_min` > `year_max`, ano 1887, `genre_mode`, `status`, `reviews` e `sort` inválidos, `min_stars` 0 e 6 | CA-21 |
| Sem filtros, o resultado é idêntico ao da 001                           | —            |

A migração 0004 é testada ida, volta e ida de novo num banco temporário,
com `alembic check`, e depois aplicada no `moviestars.db`.

### Desempenho (RNF-1, com o `moviestars.db`)

Pela API, cada caso abaixo deve ficar abaixo de 1 s:
- `sort=rating` e `sort=rating&reverse=true`, na página 1 e na última;
- `sort=reviews`;
- `min_stars=4`;
- três gêneros com `any`;
- dois gêneros com `all`;
- `reviews=without`;
- uma combinação de tudo com `search`.

### Frontend

- `build` e `lint`.
- Um script temporário com `bun` confere o `catalogFilters.ts`: ler e gravar
  ida e volta, valores inválidos ignorados, contagem de filtros ativos e
  validação dos anos com as mesmas mensagens da API.
- Um roteiro Playwright (`check_filters.py`) contra o **`moviestars.db` real**,
  porque filtrar só lê dados. Ele cobre:
  - cada filtro e a chave "Qualquer um"/"Todos";
  - uma única requisição ao digitar um ano;
  - o erro de "de" maior que "até";
  - "Sem avaliação" desabilitando as estrelas;
  - "Inverter" e a troca de campo;
  - recarregar e o voltar do navegador;
  - valores e gênero inválidos na URL;
  - "Limpar filtros" mantendo a busca;
  - o resultado vazio;
  - 360 px.
- As regressões das features 001 a 004 rodam numa cópia do banco (como na
  004).

## Decisões

- **DEC-1. Nomes dos parâmetros em inglês** (`genre`, `year_min`, `sort`…),
  como os que já existem (`page`, `page_size`, `search`, seção 4.6 da
  constituição). Os valores de domínio continuam em português (nomes de
  gênero, status).
  *Descartado:* nomes em português, o que misturaria dois idiomas na mesma
  URL.
- **DEC-2. Modelo de consulta Pydantic (`CatalogQuery`).** Os 12 parâmetros
  e as validações cruzadas (ano inicial maior que o final) ficam num lugar
  só, com as mesmas mensagens do resto da API.
  *Descartado:* 12 `Query(...)` soltos na rota, com a validação cruzada
  escrita à mão.
- **DEC-3. `list_movies` ganha `filters` opcional.** A 001 e os testes dela
  não mudam.
  *Descartado:* trocar a assinatura inteira, o que exigiria reescrever as 17
  chamadas dos testes.
- **DEC-4. O agregado de avaliações só entra quando algo precisa dele.** O
  catálogo sem esses filtros e ordenações fica tão rápido quanto hoje (spec,
  D-10).
- **DEC-5. `NOT EXISTS` para "Sem avaliação"**, em vez de juntar o agregado
  e filtrar os vazios. O índice existente responde sem calcular médias.
- **DEC-6. O mínimo de estrelas compara a média arredondada a 1 casa**
  (`ROUND(média/2, 1)`), a mesma que o cartão mostra (CA-8).
  *Limite conhecido:* o `ROUND` do SQLite e o `round` do Python podem
  divergir em valores que caem exatamente na metade (spec, "Consequências
  conhecidas").
- **DEC-7. `NULLS LAST` do SQLite (3.30+; o projeto usa 3.53)** para manter
  os valores vazios no fim nas duas direções (CA-15).
  *Descartado:* ordenar por uma expressão `IS NULL` extra, que dá o mesmo
  resultado com menos clareza.
- **DEC-8. Migração 0004 com o índice cobridor de avaliações e o índice de
  gênero**, e sem o índice antigo, que ficou redundante. Os dois índices
  novos vêm das medições do desenho (abordagem A) e deste plan.
- **DEC-9. Gêneros pelo nome, sem validação de existência na API,** como na
  busca por título: um nome desconhecido só não encontra filmes. A interface
  limpa os inválidos da URL (D-14 da spec).
  *Descartado:* 422 para gênero inexistente, o que quebraria um endereço
  compartilhado se um gênero fosse renomeado.
- **DEC-10. `QueryParams` do cliente aceita listas e booleanos,** o que é
  necessário para `genre=Drama&genre=Horror` e `reverse=true`.
- **DEC-11. Hook `useGenres` compartilhado.** O painel e a limpeza de gêneros
  inválidos precisam da lista mesmo com o painel fechado.
  *Descartado:* deixar a busca dos gêneros só dentro do `GenrePicker`, que
  não existe na tela enquanto o painel está fechado.
- **DEC-12. Os campos de ano têm estado próprio, com espera de 400 ms, e só
  gravam valores válidos na URL.** Com erro, a lista não muda (CA-5).
- **DEC-13. O roteiro dos filtros roda no banco real (só leitura), e as
  regressões numa cópia,** porque os roteiros da 003 e da 004 gravam dados.
- **DEC-14. Nenhuma dependência nova.**

## Riscos

- **Ordenar os 95.645 filmes pela média:** a medição do desenho deu cerca de
  490 ms no arquivo real sem o índice cobridor. Com o índice, a expectativa é
  ficar abaixo disso. Se passar de 1 s, a alternativa registrada é a
  abordagem B (média pronta em cada filme), que exige mudar a constituição.
- **Remover o índice antigo de avaliações:** as consultas da 002 (lista por
  filme) e da 003 (cascata) passam a usar o índice novo. As regressões e a
  medição da 002 conferem que continuam rápidas.
