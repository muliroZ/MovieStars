# 001 — Catálogo e busca — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Aprovado                                              |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 3, 4.1, 4.2, 4.6, 5, 6) |

## Visão geral

```text
Frontend (CatalogPage)                         Backend
┌──────────────────────────┐   GET /api/v1/movies?page=&page_size=&search=
│ URL ?page=3&search=ring  │ ───────────────────────────────►  router.py
│ SearchBar (debounce 300) │                                     │
│ MovieCard × 20           │ ◄───────────────────────────────  service.py
│ Pagination               │   { items, total, page,            │  1. COUNT com filtro
└──────────────────────────┘     page_size, pages }             │  2. página ordenada + gêneros/pessoas
                                                                │  3. média e quantidade das avaliações
                                                                ▼
                                                  dim_movies.titulo_normalizado (indexado)
```

O ponto central do backend é uma coluna nova, `titulo_normalizado`, em
`dim_movies`. Ela guarda o título em minúsculas e sem acentos, e tem um
índice. A busca e a ordenação usam essa coluna, o que atende a D-4 da spec
(ignorar acentos) e o RNF-1 (até 1 s por página).

## Backend

### Normalização do título (CA-2, CA-11)

Arquivo novo `backend/app/movies/normalization.py`:

```python
def normalize_title(text: str) -> str:
    """Título para busca e ordenação: sem acentos e sem diferença de maiúsculas."""
    # NFKD separa letra e acento ("À" → "A" + "̀"); os acentos são descartados.
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.casefold()
```

| Título                 | `titulo_normalizado`   |
|------------------------|------------------------|
| `À La Recherche`       | `a la recherche`       |
| `A Instalação Do Medo` | `a instalacao do medo` |
| `"""blessed"""`        | `"""blessed"""` (aspas ficam, D-1) |

A mesma função normaliza o termo digitado na busca, então os dois lados da
comparação ficam no mesmo formato.

### Mudança no modelo e migração

`backend/app/movies/models.py`, em `DimMovie`:

```python
titulo_normalizado: Mapped[str] = mapped_column(
    String(500), default=_normalized_title, server_default=""
)
# em __table_args__:
Index("ix_dim_movies_ordem_catalogo", "titulo_normalizado", "ano_lancamento", "sk_movie_id")
```

- `default=_normalized_title` é uma função que o SQLAlchemy chama a cada
  insert. Ela lê o `titulo` da própria linha
  (`context.get_current_parameters()`) e devolve o título normalizado. Isso
  funciona nos inserts do ORM (feature 003) e nos inserts em lote da carga
  (feature 000). Testei os dois antes de escrever este plan.
- `server_default=""` permite criar a coluna como `NOT NULL` numa tabela que
  já tem dados, sem recriá-la. Como efeito, a carga da feature 000 já não
  exige essa coluna nos CSVs, porque `expected_columns` ignora colunas com
  valor padrão no banco. Assim, `load_data.py` continua sem alteração.
- O índice composto cobre a ordenação completa do CA-2 (título normalizado,
  ano, chave). Com isso, qualquer página sai em menos de 1 ms, inclusive a
  última.

Migração nova `backend/migrations/versions/0002_titulo_normalizado.py`:

1. `add_column("dim_movies", titulo_normalizado String(500) NOT NULL DEFAULT '')`;
2. preenche as linhas existentes em lotes: lê `sk_movie_id, titulo`, calcula
   a normalização em Python e grava com `UPDATE`;
3. `create_index("ix_dim_movies_ordem_catalogo", ...)`.

O `downgrade` remove o índice e a coluna. A migração tem **uma cópia** da
função de normalização (DEC-3).

### Endpoint

`GET /api/v1/movies`, registrado em `app/api/v1/router.py` com o prefixo
`/movies`.

| Parâmetro   | Tipo  | Padrão | Validação (422 se falhar) | CA        |
|-------------|-------|--------|---------------------------|-----------|
| `page`      | int   | 1      | ≥ 1                       | CA-25     |
| `page_size` | int   | 20     | entre 1 e 100             | CA-25     |
| `search`    | str   | vazio  | até 200 caracteres        | CA-26     |

Resposta `200` (`MoviePage`):

```json
{
  "items": [
    {
      "sk_movie_id": "b5c3…",
      "titulo": "Rings",
      "ano_lancamento": 2017,
      "url_poster": "https://image.tmdb.org/t/p/w500/…jpg",
      "media_estrelas": 2.3,
      "qtd_avaliacoes": 3,
      "generos": ["Drama", "Horror"],
      "diretores": ["F. Javier Gutiérrez"]
    }
  ],
  "total": 95645,
  "page": 1,
  "page_size": 20,
  "pages": 4783
}
```

- `pages = ceil(total / page_size)`, com `0` quando `total = 0`
  (constituição, seção 4.6).
- Página além da última: `200` com `items: []` e `total` e `pages` corretos.
  A interface decide a mensagem (CA-24, DEC-11).
- `media_estrelas`: `null` quando não há avaliações; `qtd_avaliacoes: 0`.
- `generos` e `diretores` vêm **completos**. O corte em "+N" é feito na
  interface (DEC-6).

### Schemas (`backend/app/movies/schemas.py`, novo)

| Schema          | Campos                                                         |
|-----------------|----------------------------------------------------------------|
| `MovieListItem` | `sk_movie_id`, `titulo`, `ano_lancamento`, `url_poster`, `media_estrelas`, `qtd_avaliacoes`, `generos`, `diretores` |
| `MoviePage`     | `items: list[MovieListItem]`, `total`, `page`, `page_size`, `pages` |

### Consultas (`backend/app/movies/service.py`, novo)

`list_movies(db, page, page_size, search) -> MoviePage`:

1. **Filtro:** `term = normalize_title(search.strip())`. Se `term` não for
   vazio: `DimMovie.titulo_normalizado.contains(term, autoescape=True)`.
   O `autoescape` faz `%` e `_` serem texto comum (CA-13).
2. **Total:** `SELECT COUNT(*) FROM dim_movies WHERE <filtro>`.
3. **Página:**
   ```python
   select(DimMovie).where(<filtro>)
       .order_by(DimMovie.titulo_normalizado, DimMovie.ano_lancamento, DimMovie.sk_movie_id)
       .offset((page - 1) * page_size).limit(page_size)
       .options(selectinload(DimMovie.genres), selectinload(DimMovie.people))
   ```
   Os `selectinload` carregam gêneros e pessoas dos 20 filmes em duas
   consultas extras, e não uma por filme. Também evitam o erro
   `MissingGreenlet` descrito no `CLAUDE.md`.
4. **Avaliações** dos filmes da página (CA-7):
   ```sql
   SELECT sk_movie_id, AVG(nota), COUNT(*) FROM movie_reviews
   WHERE sk_movie_id IN (<ids da página>) GROUP BY sk_movie_id
   ```
   `media_estrelas = round(avg / 2, 1)`: esta é a conversão de 0–10 para
   estrelas, feita só no serviço (constituição, seção 4.1).
5. **Montagem:** `generos` na ordem do relacionamento (alfabética);
   `diretores` = pessoas com `tipo_pessoa == "Diretor"`, em ordem
   alfabética.

A página inteira usa 5 consultas pequenas: total, filmes, gêneros, pessoas e
avaliações.

### Rota (`backend/app/movies/router.py`, novo)

Rota fina: recebe os parâmetros com `Query(...)`, que já aplica as
validações da tabela acima, chama `list_movies` e declara
`response_model=MoviePage`.

## Frontend

### Dependência e configuração

- `react-router-dom` (nova dependência, DEC-8), instalada com `bun add`.
- `tsconfig.app.json`: acrescentar `"strict": true` (DEC-9).
- `src/vite-env.d.ts`: tipa `VITE_API_URL` como `string | undefined`, para
  não cair em `any`.
- `index.html`: `lang="pt-BR"`.
- `public/poster-placeholder.svg`: a imagem padrão do pôster (CA-6).

### Rotas (`src/App.tsx`)

| Rota               | Componente                          |
|--------------------|-------------------------------------|
| `/`                | `CatalogPage`                       |
| `*`                | `NotFoundPage` ("Página não encontrada" + link para o catálogo) |

O cartão aponta para `/filmes/:skMovieId` (CA-9). Até a feature 002 criar
essa rota, o link cai na `NotFoundPage` (DEC-12).

### Arquivos e responsabilidades

| Arquivo                          | Responsabilidade                                         | CAs |
|----------------------------------|----------------------------------------------------------|-----|
| `src/types/movie.ts`             | `MovieListItem` e `Page<T>`, espelhando os schemas       | —   |
| `src/api/client.ts`              | `API_URL` (de `VITE_API_URL`, padrão `http://localhost:8000/api/v1`); `apiGet<T>(path, params, signal)`, que lança `ApiError` com mensagem em português | CA-22 |
| `src/api/movies.ts`              | `listMovies({ page, pageSize, search }, signal)`         | —   |
| `src/hooks/useDebounce.ts`       | Devolve o valor depois de X ms sem mudanças              | CA-14 |
| `src/hooks/useMovies.ts`         | Busca a página e expõe `status` (`loading`, `error`, `success`), `data`, `error` e `retry()`; cancela a requisição anterior com `AbortController` | CA-21, CA-22 |
| `src/pages/CatalogPage.tsx`      | Lê e grava `page` e `search` na URL; junta busca, resumo, grade, paginação e estados | CA-1, CA-3, CA-5, CA-12, CA-15 a CA-20, CA-23, CA-24 |
| `src/pages/NotFoundPage.tsx`     | Rota coringa                                             | —   |
| `src/components/SearchBar.tsx`   | Campo com `maxLength=200` e botão "Limpar"               | CA-17, CA-26 |
| `src/components/MovieCard.tsx`   | Pôster (com troca para a imagem padrão em `onError`), título cortado com `title`, ano, estrelas, gêneros (3 + "+N"), diretores (2 + "e mais N") | CA-6, CA-8, CA-9 |
| `src/components/StarRating.tsx`  | 5 estrelas com meia estrela, número com 1 casa ("3,5") e quantidade | CA-6, CA-7 |
| `src/components/Pagination.tsx`  | Primeira, anterior, "Página X de Y", próxima e última, com os limites desabilitados | CA-3, CA-4 |
| `src/components/LoadingState.tsx`, `ErrorState.tsx`, `EmptyState.tsx` | Os três estados da constituição | CA-21 a CA-24 |
| `src/index.css` e um `.css` por componente | Estilos simples, grade responsiva a partir de 360 px | CA-27 |

### Estado na URL (CA-12, CA-16, CA-18 a CA-20)

- A URL guarda `page` e `search`. O padrão é omitido: `page=1` e busca
  vazia não aparecem, e `/` é a página 1 sem busca.
- `page` lido da URL: se não for um inteiro ≥ 1, vale 1 (CA-20).
- O campo de busca tem estado local, para não pesar a cada tecla. O valor
  com debounce vai para a URL como `search=<termo sem espaços nas pontas>`
  e remove `page`, o que volta para a página 1 (CA-16).
- Cada mudança de página ou de busca **cria uma entrada no histórico**, e é
  isso que faz os botões voltar e avançar do navegador funcionarem
  (CA-19). Quando a URL muda pelo voltar, o campo de busca é atualizado
  com o valor dela.
- Ao trocar de página: `window.scrollTo({ top: 0 })` (CA-5).

### Textos e formatação

- Números: `toLocaleString("pt-BR")`, que dá "95.645" e "3,5".
- Plural: "1 filme" / "N filmes"; "1 avaliação" / "N avaliações".
- Resumo: "95.645 filmes" sem busca; "37 filmes encontrados para "ring""
  com busca (CA-15).
- Estados:
  - catálogo vazio: "Nenhum filme cadastrado";
  - busca sem resultado: "Nenhum filme encontrado para "<termo>"";
  - página além da última: "Esta página não existe";
  - erro: "Não foi possível carregar os filmes." com "Tentar novamente".

## Arquivos

| Arquivo                                                | Ação    |
|--------------------------------------------------------|---------|
| `backend/app/movies/normalization.py`                  | Criar   |
| `backend/app/movies/models.py`                         | Alterar (coluna + índice) |
| `backend/migrations/versions/0002_titulo_normalizado.py` | Criar |
| `backend/app/movies/schemas.py`                        | Criar   |
| `backend/app/movies/service.py`                        | Criar   |
| `backend/app/movies/router.py`                         | Criar   |
| `backend/app/api/v1/router.py`                         | Alterar (registrar `/movies`) |
| `backend/tests/conftest.py`                            | Criar (banco temporário assíncrono + cliente HTTP) |
| `backend/tests/test_normalization.py`                  | Criar   |
| `backend/tests/test_movies_api.py`                     | Criar   |
| `backend/tests/test_load_data.py`                      | Alterar (conferir `titulo_normalizado` preenchido na carga) |
| `frontend/package.json`, `bun.lock`                    | Alterar (`react-router-dom`) |
| `frontend/tsconfig.app.json`, `index.html`             | Alterar |
| `frontend/public/poster-placeholder.svg`               | Criar   |
| `frontend/src/**` (tabela acima)                       | Criar / alterar `App.tsx`, `main.tsx`, `index.css` |
| `README.md`                                            | Alterar (decisões, status, frontend) |
| `CLAUDE.md`                                            | Alterar (armadilha: manter `titulo_normalizado` em dia ao editar título) |

## Testes

### Backend (pytest)

`conftest.py` cria, para cada teste, um banco SQLite temporário
(`sqlite+aiosqlite`) com `Base.metadata.create_all`. Ele substitui o
`get_db` da aplicação (`app.dependency_overrides`) e fornece um
`httpx.AsyncClient` com `ASGITransport`, no padrão de `test_app.py`
(constituição, seção 6). Os dados de teste são inseridos pelo ORM.

| Teste                                                              | CAs          |
|--------------------------------------------------------------------|--------------|
| `normalize_title`: acentos, maiúsculas, `ß`, aspas preservadas     | CA-2, CA-11  |
| Página 1 com `total`, `pages`, `page_size` e 20 itens              | CA-1, CA-3   |
| Ordem: "À La Recherche" junto dos "A"; mesmo título por ano; desempate estável | CA-2 |
| Busca por parte do título, sem acentos e sem diferença de maiúsculas | CA-10, CA-11 |
| Espaços nas pontas ignorados; busca vazia = catálogo completo     | CA-12        |
| `%` e `_` como texto comum                                         | CA-13        |
| Busca paginada e ordenada como o catálogo                          | CA-15        |
| Página além da última: `items` vazio, `total` e `pages` corretos   | CA-24        |
| `page=0`, `page_size=0`, `page_size=101` e `search` com 201 caracteres → 422 | CA-25, CA-26 |
| Média em estrelas arredondada, quantidade, `null` sem avaliações   | CA-6, CA-7   |
| Gêneros em ordem alfabética; só pessoas "Diretor" em `diretores`, em ordem alfabética | CA-6 |
| Filme inserido pelo ORM recebe `titulo_normalizado`                | CA-2         |
| Carga da 000 preenche `titulo_normalizado`                         | CA-2         |

### Frontend

A constituição deixa testes de frontend para as features 100+. A
verificação é feita com `bun run build` e `bun run lint` e com um roteiro
manual no navegador, cobrindo cada CA da interface. Inclui a largura de
360 px e os estados de carregamento, erro (API desligada) e vazio.

### Com os dados reais

- `alembic upgrade head` no `moviestars.db`: nenhuma linha com
  `titulo_normalizado` vazio.
- Tempo de resposta da API (RNF-1): página 1, última página, busca "ring" e
  busca "a" (muitos resultados). Todas devem ficar abaixo de 1 s.

## Decisões

- **DEC-1. Coluna `titulo_normalizado` com índice composto.** Medição com
  os 95.645 títulos reais: a coluna indexada responde em 0,0 a 6,8 ms, e a
  função Python aplicada na consulta leva de 123 a 295 ms, antes ainda da
  contagem e da latência da API.
  *Descartado:* função de normalização registrada no SQLite e aplicada a
  cada consulta, que é lenta e pesa mais nas páginas finais.
  *Descartado:* busca textual FTS5 do SQLite, que procura palavras inteiras
  e não pedaços do título (CA-10), além de ser mais complexa.
- **DEC-2. Preenchimento pelo `default` do SQLAlchemy, com
  `server_default=""`.** É um mecanismo só, que vale para a carga (000) e
  para o ORM (003), e a carga não precisa mudar.
  *Descartado:* alterar o `load_data.py` para calcular a coluna, o que
  reabriria a feature 000. *Descartado:* um gatilho (trigger) no SQLite, que
  não sabe remover acentos. *Limite conhecido:* o `default` só roda no
  insert. A feature 003, ao editar um título, precisa atualizar
  `titulo_normalizado` também. Isso fica registrado no `CLAUDE.md`.
- **DEC-3. A migração tem sua própria cópia da normalização.** Uma migração
  deve dar sempre o mesmo resultado, mesmo que o código da aplicação mude
  depois.
  *Descartado:* importar `normalize_title` de `app/`.
- **DEC-4. `contains(..., autoescape=True)` do SQLAlchemy para a busca.**
  Ele escapa `%` e `_` sozinho (CA-13).
  *Descartado:* montar o `LIKE` e escapar os caracteres à mão.
- **DEC-5. Cinco consultas pequenas por página**: total, filmes, gêneros,
  pessoas e avaliações. Cada uma é simples de ler e testar, e nenhuma cresce
  com o número de filmes da página (sem N+1).
  *Descartado:* uma única consulta com junções e agregações, mais difícil de
  entender.
- **DEC-6. A API devolve gêneros e diretores completos; a interface corta
  em "+N".** A feature 002 reaproveita os mesmos dados sem corte.
  *Descartado:* cortar no backend.
- **DEC-7. `MoviePage` específico, não genérico.** É o único endpoint
  paginado por enquanto. Se surgir outro, vira um `Page[T]` genérico.
  *Descartado:* criar o genérico agora.
- **DEC-8. Nova dependência: `react-router-dom`.** A constituição exige
  (seção 5.3), e ela ainda não estava no `package.json`.
- **DEC-9. `"strict": true` no `tsconfig.app.json`.** A constituição exige
  o modo estrito, e o projeto base não o ativava.
- **DEC-10. CSS simples, um arquivo por componente, sem biblioteca de
  interface.** Não traz dependências novas e é suficiente para uma tela.
  *Descartado:* Tailwind ou bibliotecas de componentes, que exigiriam
  dependências e justificativa.
- **DEC-11. Página além da última devolve `200` com `items: []`.** Os
  campos `total` e `pages` deixam a interface mostrar a mensagem do CA-24.
  *Descartado:* `404`, que trataria uma página vazia como erro.
- **DEC-12. Rota coringa `NotFoundPage`.** Enquanto a feature 002 não
  existir, clicar num cartão mostra "Página não encontrada" em vez de uma
  tela em branco.
- **DEC-13. Cada mudança de página ou de busca cria uma entrada no
  histórico.** É o que faz o voltar e o avançar do navegador funcionarem
  (CA-19). Como a busca só vai para a URL depois do debounce, não surge uma
  entrada por tecla.
  *Descartado:* substituir a entrada atual (`replace`), o que quebraria o
  CA-19.

## Riscos

- **Migração no `moviestars.db` (550 MB):** a migração acrescenta uma coluna
  e preenche 95.645 linhas numa transação. Se falhar, o Alembic desfaz. A
  estimativa é de poucos segundos.
- **Edição de títulos (feature 003):** se o `titulo_normalizado` não for
  atualizado junto com o título, a busca e a ordem ficam erradas para
  aquele filme (DEC-2).
- **Pôsteres externos:** 20 imagens de `w500` do TMDB por página. É
  aceitável; trocar por um tamanho menor seria transformar dados (spec 000,
  D-4).
