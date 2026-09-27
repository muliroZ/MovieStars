# 101 — Cache de consultas — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Aprovado                                              |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 3, 5.2, 6); plan 100 (DEC-2, DEC-15, Riscos) |

## Visão geral

```text
GET /api/v1/movies?...   GET /api/v1/genres
        │                        │
        ▼                        ▼
 router (app/movies/router.py) ── _cached(chave, response, calcular)
        │   cache desligado → calcula; X-Cache: BYPASS
        │   acerto          → devolve o guardado; X-Cache: HIT
        │   falha           → anota a geração, calcula, guarda se a geração
        │                     não mudou; X-Cache: MISS
        ▼
 service (list_movies, list_genres) ── sem mudança

POST/PUT/DELETE /movies, POST /movies/{id}/reviews
        ▼
 service (create_movie, update_movie, delete_movie, create_review)
   await db.commit()
   query_cache.clear()   ← esvazia tudo e incrementa a geração
```

Só o backend muda. O frontend não precisa de nada: as respostas têm o mesmo
corpo, e o cabeçalho `X-Cache` só aparece nas ferramentas do navegador.

## Backend

### Módulo `app/core/cache.py` (novo; DEC-1, DEC-4, DEC-9)

Uma classe pequena, `QueryCache`, e uma instância global da aplicação.

```python
MISSING = object()  # sentinela: "não há valor guardado" (None pode ser um valor)

class QueryCache:
    def __init__(self, *, enabled: bool = True, ttl_seconds: float = 300,
                 max_entries: int = 256, clock: Callable[[], float] = time.monotonic): ...
    enabled: bool                 # atributos públicos: os testes trocam com monkeypatch
    ttl_seconds: float
    max_entries: int
    clock: Callable[[], float]
    generation: int               # propriedade, só leitura

    def get(self, key: str) -> object: ...
    def set(self, key: str, value: object, generation: int) -> None: ...
    def clear(self) -> None: ...
    def __len__(self) -> int: ...

query_cache = QueryCache(enabled=..., ttl_seconds=..., max_entries=...)  # da Settings
```

| Método   | Comportamento                                                        | CAs |
|----------|----------------------------------------------------------------------|-----|
| `get`    | Devolve o valor e o move para o fim do `OrderedDict` (usado agora). Se não existe ou expirou (`clock() >= guardado_em + ttl`), remove a entrada expirada e devolve `MISSING` | CA-1, CA-13, CA-14 |
| `set`    | Se `generation` for diferente da geração atual, não guarda nada (DEC-4). Senão, guarda `(clock(), valor)` no fim e, passando de `max_entries`, remove do início (a menos usada recentemente) | CA-12, CA-14 |
| `clear`  | Esvazia tudo e incrementa a geração                                  | CA-8 a CA-10, CA-12 |

- As entradas expiradas que ninguém lê ficam até serem descartadas pelo
  limite; com 256 entradas, isso não pesa.
- O `enabled` é conferido pelo router, não pela classe, para que o router
  saiba responder `BYPASS` (DEC-6).
- Não há `await` dentro dos métodos, e a aplicação roda num único processo
  com um único laço de eventos: nenhum método é interrompido no meio, então
  não é preciso trava (DEC-8).

### Leitura no router (`app/movies/router.py`; DEC-5, DEC-6)

Uma função de apoio usada pelas duas rotas:

```python
async def _cached(key: str, response: Response, compute: Callable[[], Awaitable[T]]) -> T:
    if not query_cache.enabled:
        response.headers["X-Cache"] = "BYPASS"
        return await compute()
    value = query_cache.get(key)
    if value is not MISSING:
        response.headers["X-Cache"] = "HIT"
        return value
    generation = query_cache.generation      # antes de ir ao banco (DEC-4)
    value = await compute()
    query_cache.set(key, value, generation)
    response.headers["X-Cache"] = "MISS"
    return value
```

| Rota          | Chave                                          | CAs |
|---------------|------------------------------------------------|-----|
| `GET /movies` | `"movies:" + _catalog_key(query)` (DEC-2)      | CA-1 a CA-3, CA-7 |
| `GET /genres` | `"genres"`                                     | CA-4, CA-7 |

- `get_movies` e `read_genres` ganham o parâmetro `response: Response`, e o
  corpo passa a ser `return await _cached(chave, response, lambda: list_movies(...))`.
- `_catalog_key(query)`: `query.model_dump(mode="json")`, com `genre` e
  `status` ordenados, serializado com `json.dumps(..., sort_keys=True)`.
  Todos os campos entram, inclusive `page`, `page_size` e `search`, então
  qualquer diferença gera outra chave (CA-3).
- Uma requisição inválida é recusada pelo FastAPI antes de a rota rodar:
  o 422 não passa pelo cache e não tem `X-Cache` (CA-5).
- Detalhes, avaliações e diretores não mudam (CA-6).
- O valor guardado é o próprio objeto devolvido pelo serviço
  (`Page[MovieListItem]` ou `list[str]`), que ninguém altera depois (DEC-9).

### Limpeza no serviço (`app/movies/service.py`; DEC-3, DEC-5)

`query_cache.clear()` logo depois do `await db.commit()`:

| Função          | Onde                                                  | CAs |
|-----------------|-------------------------------------------------------|-----|
| `create_movie`  | depois do `commit`                                    | CA-9 |
| `update_movie`  | depois do `commit` (o `return None` de filme inexistente vem antes) | CA-9, CA-11 |
| `delete_movie`  | depois do `commit`, **só se `rowcount > 0`**; remover um filme inexistente não limpa | CA-9, CA-11 |
| `create_review` | depois do `commit` (o `return None` de filme inexistente vem antes) | CA-8, CA-11 |

- Gênero inexistente (`UnknownGenresError`) e erros de validação acontecem
  antes do `commit`, então não limpam (CA-11).
- Se o `commit` falhar, a exceção sobe e a limpeza não acontece: nada mudou
  no banco.
- `list_movies` e `list_genres` não mudam, e os testes de serviço também não.

### Configuração (`app/core/config.py` e `.env.example`; DEC-7)

| `Settings`          | Variável            | Tipo e validação           | Padrão |
|---------------------|---------------------|----------------------------|--------|
| `cache_enabled`     | `CACHE_ENABLED`     | `bool`                     | `True` |
| `cache_ttl_seconds` | `CACHE_TTL_SECONDS` | `int`, maior que 0         | `300`  |
| `cache_max_entries` | `CACHE_MAX_ENTRIES` | `int`, maior que 0         | `256`  |

- Um valor inválido (ex.: `CACHE_TTL_SECONDS=0` ou `abc`) faz o `Settings`
  falhar ao iniciar a aplicação, com o nome da variável na mensagem do
  Pydantic (caso de borda da spec).
- O `.env.example` ganha as três variáveis com os padrões. O `.env` de cada
  desenvolvedor não é tocado: sem as variáveis, valem os padrões.

### Arquivos do backend

| Arquivo                        | Ação                                                   |
|--------------------------------|--------------------------------------------------------|
| `app/core/cache.py`            | criar (`QueryCache`, `MISSING`, `query_cache`)         |
| `app/core/config.py`           | três campos novos                                      |
| `app/movies/router.py`         | `_cached`, `_catalog_key`; `get_movies` e `read_genres` com `response` |
| `app/movies/service.py`        | `query_cache.clear()` nas quatro escritas              |
| `.env.example`                 | três variáveis                                         |
| `tests/conftest.py`            | fixture `autouse` que limpa o cache                    |
| `tests/test_cache.py`          | criar (unitários da classe)                            |
| `tests/test_cache_api.py`      | criar (API)                                            |

Não há migração nem mudança no frontend.

## Testes

### Isolamento (DEC-10)

- `conftest.py` ganha uma fixture `autouse` que chama `query_cache.clear()`
  antes de cada teste. Sem ela, um resultado guardado num teste seria
  devolvido em outro, que usa outro banco temporário.
- Os testes que mudam `enabled`, `clock` ou `max_entries` da instância global
  usam `monkeypatch.setattr`, que desfaz a troca no fim do teste.
- Verificado ao escrever o plan: nenhum teste atual consulta o catálogo pela
  API, grava direto pela sessão e consulta de novo. Então a limpeza antes de
  cada teste basta, e os testes atuais não mudam.

### Unitários (`tests/test_cache.py`)

Com uma instância própria e um relógio falso (uma lista com o "agora" que o
teste avança), sem `sleep`:

| Teste                                                                   | CAs          |
|-------------------------------------------------------------------------|--------------|
| `get` sem valor devolve `MISSING`; `set` e `get` devolvem o valor; `None` pode ser guardado | CA-1 |
| Expira em `ttl` (um instante antes ainda vale; no limite, não)          | CA-13        |
| Passando de `max_entries`, sai a menos usada; um `get` a torna a mais usada | CA-14    |
| Guardar a mesma chave de novo substitui o valor e a torna a mais usada  | CA-14        |
| `clear` esvazia e incrementa a geração                                  | CA-10        |
| `set` com geração antiga não guarda                                     | CA-12        |

### API (`tests/test_cache_api.py`)

Pelo `client` do `conftest.py`, com filmes montados por `helpers.add_movie`:

| Teste                                                                   | CAs          |
|-------------------------------------------------------------------------|--------------|
| Duas vezes a mesma consulta: `MISS` e depois `HIT`, com o mesmo JSON    | CA-1, CA-7   |
| `genre=Drama&genre=Horror` e depois `genre=Horror&genre=Drama` (e o mesmo com `status`): `HIT` | CA-2 |
| Mudar `page`, `page_size`, `search`, um filtro, `sort` ou `reverse`: `MISS` | CA-3     |
| `GET /genres`: `MISS` e depois `HIT`                                    | CA-4, CA-7   |
| 422 sem `X-Cache`; a consulta corrigida vem com `MISS`                  | CA-5         |
| Detalhes, avaliações e diretores sem `X-Cache`                          | CA-6         |
| Avaliação nova: o próximo `GET /movies?sort=rating` vem com `MISS` e com a nova média, a nova quantidade e a nova ordem; o mesmo com `min_stars` | CA-8 |
| Cadastrar, atualizar (título) e remover: `MISS` com o filme novo, o título novo ou sem o filme, e o `total` certo | CA-9 |
| Depois de uma escrita, `GET /genres` e uma consulta sem relação com o filme também vêm com `MISS` | CA-10 |
| Avaliação em filme inexistente (404), cadastro com gênero inexistente (422), edição e remoção de filme inexistente (404): a consulta seguinte continua `HIT` | CA-11 |
| Corrida: o `list_movies` da rota é trocado por um que chama o original e depois `query_cache.clear()` (uma escrita que termina durante a consulta); a resposta vem com `MISS`, e a seguinte também | CA-12 |
| Relógio falso: 299 s depois, `HIT`; 300 s depois, `MISS`                | CA-13        |
| `max_entries=2`: três consultas diferentes, e a primeira volta com `MISS` | CA-14      |
| `enabled=False`: duas consultas iguais com `BYPASS`, e nada guardado    | CA-15        |
| `Settings`: padrões `True`, 300 e 256; `cache_ttl_seconds=0` e `cache_max_entries=0` recusados | CA-16 |
| Mesma consulta com o cache ligado e desligado: mesmo status e mesmo JSON | CA-17       |

### Desempenho (RNF-1, RNF-2)

Pela API, com o `moviestars.db` (só leituras), 5 execuções de cada, anotando
o pior tempo na seção "Riscos":
- `sort=rating`, última página: `MISS` e `HIT`;
- `sort=reviews`, última página: `MISS` e `HIT`;
- sem filtros, página 1: `MISS` e `HIT`;
- `GET /genres`: `MISS` e `HIT`.

Os `MISS` são comparados com os tempos do plan 100 (RNF-2). Como não existe
rota para esvaziar o cache (fora de escopo), o script reinicia a API antes de
cada execução, e a primeira requisição de cada consulta é o `MISS`.

### Regressões

- `pytest` inteiro com o cache ligado (o padrão).
- Os roteiros de navegador da 001 a 004 e da 100 numa cópia do banco. As
  escritas da 003 e da 004 conferem, pela tela, que o catálogo mostra os
  dados novos logo depois de cada alteração.

## Decisões

Os detalhes técnicos das decisões D-1 a D-9 da spec, e as decisões novas
deste plan.

- **DEC-1. Classe própria em `app/core/cache.py`, com `OrderedDict`** (spec,
  D-1 e D-7). O `OrderedDict` guarda a ordem de uso: `move_to_end` no acerto e
  `popitem(last=False)` para descartar a menos usada recentemente, com a
  expiração conferida na leitura. São cerca de 40 linhas.
  *Descartado:*
  - Redis: um serviço a mais, sem ganho com um único processo e SQLite local;
  - `cachetools`: uma dependência nova para cerca de 40 linhas;
  - TanStack Query no frontend: exigiria reescrever os quatro hooks de busca
    (`useMovies`, `useMovie`, `useMovieReviews`, `useGenres`).
- **DEC-2. Chave derivada do `CatalogQuery` já validado** (spec, D-3), com
  `genre` e `status` ordenados e `json.dumps(sort_keys=True)`. Como a chave vem
  do modelo validado, `reverse=true` e `reverse=1`, por exemplo, viram o mesmo
  valor e a mesma chave.
  *Descartado:* usar o texto da URL, que trataria como diferentes consultas
  iguais escritas de outro jeito.
- **DEC-3. `query_cache.clear()` logo depois do `commit`** das quatro escritas
  (spec, D-4): `create_movie`, `update_movie`, `delete_movie` e
  `create_review`. Na remoção, só quando o filme existia (`rowcount > 0`),
  para cumprir o CA-11.
- **DEC-4. Contador de geração** (spec, D-5). `clear` incrementa a geração;
  numa falha, o router anota a geração antes de consultar o banco, e o `set`
  só guarda se ela não mudou. Uma consulta iniciada antes de uma escrita não
  grava um resultado velho depois da limpeza.
  *Descartado:* uma trava que bloqueie leituras durante as escritas, mais
  complexa e desnecessária com um único laço de eventos.
- **DEC-5. Leitura no router, limpeza no serviço.** O router consulta o cache
  e só chama o serviço na falha, então o serviço continua sem estado e seus
  testes não mudam. A limpeza fica colada ao `commit`, dentro do serviço, para
  que nenhuma escrita esqueça de invalidar.
  *Descartado:* limpar no router depois de cada escrita, onde seria fácil
  esquecer uma rota nova.
- **DEC-6. Cabeçalho `X-Cache`** (spec, D-6): `HIT`, `MISS` ou `BYPASS` nas
  respostas de `GET /movies` e `GET /genres`. Não entra no `expose_headers` do
  CORS, porque o frontend não o lê; as ferramentas do navegador o mostram
  mesmo assim.
- **DEC-7. Configuração no `Settings` e no `.env.example`** (spec, D-8):
  `CACHE_ENABLED` (padrão `true`), `CACHE_TTL_SECONDS` (300) e
  `CACHE_MAX_ENTRIES` (256), os dois últimos maiores que 0.
- **DEC-8. Um único worker do uvicorn** (spec, D-9). O cache é por processo; o
  comando do README (`uvicorn app.main:app`) já usa um worker só. O README
  passa a dizer para não usar `--workers` maior que 1.
- **DEC-9. Guardar o objeto devolvido pelo serviço.** O FastAPI o serializa a
  cada resposta, o que custa bem menos de 1 ms para 20 filmes.
  *Descartado:* guardar o JSON pronto e devolver um `Response` cru, o que
  pularia o `response_model` e mudaria o formato das rotas.
- **DEC-10. Instância global e relógio injetado.** O serviço e o router usam a
  mesma instância, `query_cache`; os testes a limpam numa fixture `autouse` e
  trocam `clock`, `enabled` e `max_entries` com `monkeypatch`. O relógio padrão
  é `time.monotonic`, que não volta atrás se o relógio do sistema mudar.
  *Descartado:* entregar o cache por `Depends`, porque o serviço também
  precisa dele e passaria a receber mais um parâmetro em todas as escritas.
- **DEC-11. Nenhuma dependência nova.** Tudo vem da biblioteca padrão
  (`collections.OrderedDict`, `time`, `json`).

## Riscos

- **Testes que escrevem pela sessão entre duas consultas da API** receberiam o
  resultado guardado. Nenhum teste atual faz isso (conferido ao escrever o
  plan); os novos que fizerem precisam chamar `query_cache.clear()`, e o
  `CLAUDE.md` passa a avisar.
- **Uma escrita nova esquecer a limpeza.** Toda escrita futura no serviço
  precisa chamar `query_cache.clear()` depois do `commit`; o `CLAUDE.md` passa
  a avisar, e os testes do CA-8 a CA-11 cobrem as quatro atuais.
- **RNF-1 e RNF-2:** a medir na implementação (seção "Desempenho").
