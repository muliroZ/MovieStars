# 003 — Gerenciar filmes — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Aprovado                                              |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6); plans da 001 (DEC-1, DEC-2) e da 002 |

## Visão geral

```text
Catálogo ── "Novo filme" ──► /filmes/novo ──────────┐
                                                    ├─ MovieFormPage ── POST /movies ─┐
Detalhes ── "Editar" ──────► /filmes/:id/editar ────┘                  PUT  /movies/{id}
    │                            │ GET /genres (lista)                               │
    │                            └ GET /directors?search= (sugestões)                ▼
    └─ "Excluir" ─► confirmação ─► DELETE /movies/{id} ─► catálogo    Detalhes + mensagem
```

## Backend

### Endpoints novos

| Método e rota                         | Sucesso                    | Erros            | CAs |
|---------------------------------------|----------------------------|------------------|-----|
| `POST /api/v1/movies`                 | `201` + `MovieDetail`      | 422              | CA-2, CA-3, CA-6 a CA-19 |
| `PUT /api/v1/movies/{sk_movie_id}`    | `200` + `MovieDetail`      | 404, 422         | CA-20 a CA-25 |
| `DELETE /api/v1/movies/{sk_movie_id}` | `204`, sem corpo           | 404              | CA-26 a CA-30 |
| `GET /api/v1/genres`                  | `200` + lista de gêneros   | —                | CA-2, CA-13 |
| `GET /api/v1/directors?search=`       | `200` + até 10 diretores   | 422 (termo com menos de 2 ou mais de 255 caracteres) | CA-16, CA-17 |

A resposta de `POST` e `PUT` é o mesmo `MovieDetail` da 002, e a interface
vai direto para os detalhes com ele.

### Corpo de `POST` e `PUT` (`MovieInput`)

```json
{
  "titulo": "Cidade de Deus",
  "ano_lancamento": 2002,
  "status_filme": "Lançado",
  "data_lancamento": "2002-08-30",
  "duracao_minutos": 130,
  "sinopse": "Buscapé cresce…",
  "url_poster": "https://image.tmdb.org/t/p/w500/p.jpg",
  "url_backdrop": null,
  "generos": ["Crime", "Drama"],
  "diretores": ["Fernando Meirelles", "Kátia Lund"]
}
```

- **Gêneros e diretores vão pelo nome** (DEC-3). No banco, `nome_genero` é
  único, e o par (`nome_pessoa`, `tipo_pessoa`) também. Por isso o nome
  identifica um único gênero ou diretor, e o formulário de edição pode ser
  preenchido com o próprio `MovieDetail`, que já traz os nomes.
- O `PUT` recebe o mesmo corpo completo do `POST` e substitui os campos
  editáveis (DEC-2).

Validações no schema Pydantic (CA-6 a CA-13, CA-19):

| Campo            | Regra                                                        |
|------------------|--------------------------------------------------------------|
| `titulo`         | sem espaços nas pontas; 1 a 500 caracteres                   |
| `ano_lancamento` | inteiro entre 1888 e o ano atual + 10 (calculado na hora)    |
| `status_filme`   | `Literal["Lançado", "Pós-Produção", "Em Produção", "Planejado"]` |
| `data_lancamento`| data ou `null`; se houver, o ano dela = `ano_lancamento`     |
| `duracao_minutos`| inteiro de 1 a 1.000 ou `null`                               |
| `sinopse`        | até 4.000 caracteres; texto vazio vira `null`                |
| `url_poster`, `url_backdrop` | até 2.048 caracteres, começando com `http://` ou `https://`; vazio vira `null` |
| `generos`        | lista de nomes; repetidos são ignorados                      |
| `diretores`      | lista de nomes sem espaços nas pontas, de 1 a 255 caracteres; repetidos são ignorados |

Um gênero que não existe é recusado no serviço, com `422` e a mensagem
"Gênero inexistente: X." no campo `generos`.

### Mensagens de validação em português (DEC-8)

O FastAPI responde os `422` com as mensagens do Pydantic, em inglês. A
constituição (seção 5.1) pede mensagens de erro da API em português.
`app/core/errors.py` registra um tratador para `RequestValidationError` que
mantém o formato (`{"detail": [{"loc", "msg", "type"}]}`) e traduz as
mensagens dos tipos usados no projeto. Alguns exemplos:

| Tipo do Pydantic                     | Mensagem                              |
|--------------------------------------|---------------------------------------|
| `missing`                            | "Campo obrigatório."                  |
| `string_too_short`, `string_too_long`| "Deve ter entre X e Y caracteres."    |
| `greater_than_equal`, `less_than_equal` | "Deve ser no mínimo X." / "no máximo Y." |
| `int_parsing`, `date_from_datetime_parsing`, `date_parsing` | "Número inválido." / "Data inválida." |
| `literal_error`                      | "Valor inválido."                     |
| `string_pattern_mismatch`            | "Deve começar com http:// ou https://." |
| `value_error` (validadores próprios) | a mensagem do validador, já em português |

Isso vale também para os `422` das features 001 e 002, cujos testes só
conferem o código de status.

### Busca de diretores sem acentos (DEC-4)

É o mesmo padrão da DEC-1 da 001, agora para pessoas:

- `DimPerson.nome_normalizado`: `String(255)` preenchida com
  `normalize_title(nome_pessoa)` pelo `default` do SQLAlchemy no insert,
  com `server_default=""`. A carga da 000 continua sem mudança, pelo mesmo
  motivo da 001.
- Índice `ix_dim_people_tipo_nome_normalizado` (`tipo_pessoa`,
  `nome_normalizado`).
- Migração `0003_nome_normalizado_pessoas.py`: adiciona a coluna, preenche
  as 424.656 pessoas em lotes (com uma cópia própria da normalização) e
  cria o índice.

A consulta das sugestões:

```sql
SELECT nome_pessoa FROM dim_people
WHERE tipo_pessoa = 'Diretor' AND nome_normalizado LIKE '%<termo>%' ESCAPE '/'
ORDER BY nome_pessoa = :termo_original DESC,          -- nome exato primeiro
         nome_normalizado NOT LIKE '<termo>%' ESCAPE '/', -- depois os que começam com o termo
         nome_normalizado                              -- depois em ordem alfabética
LIMIT 10
```

Medição com os 65.200 diretores reais: cerca de 5 ms com a coluna
indexada, contra 104 ms com a função de normalização aplicada a cada
consulta.

### Serviço (`app/movies/service.py`)

- `list_genres(db) -> list[str]`: nomes em ordem alfabética.
- `search_directors(db, termo) -> list[str]`: a consulta acima.
- `create_movie(db, dados) -> MovieDetail`:
  1. confere os gêneros (`422` se algum não existir);
  2. resolve os diretores: um nome exato existente com `tipo_pessoa =
     "Diretor"` é reaproveitado, e os outros viram `DimPerson` novos;
  3. cria o `DimMovie` com `id_filme = str(uuid4())` (constituição, seção
     4.4);
  4. `commit` e devolve `get_movie(db, chave)`.
- `update_movie(db, chave, dados) -> MovieDetail | None`:
  1. carrega o filme com `selectinload` de gêneros e pessoas (`None` → 404);
  2. atualiza os campos e **recalcula `titulo_normalizado`** (DEC-7; a
     armadilha registrada no `CLAUDE.md`);
  3. troca os gêneros e **só os diretores** em `people`. Roteiristas e atores
     são mantidos (CA-22, DEC-6);
  4. `commit` e devolve `get_movie`.
- `delete_movie(db, chave) -> bool`: `DELETE FROM dim_movies WHERE
  sk_movie_id = :chave`. As chaves estrangeiras com `ON DELETE CASCADE`
  apagam avaliações, vínculos, métricas e resumo (DEC-5). Devolve `False`
  se nada foi apagado (→ 404).

### Rotas

Em `app/movies/router.py`:
- as três rotas de filme;
- `genres_router` (`GET ""`);
- `directors_router` (`GET ""` com `search: str = Query(min_length=2,
  max_length=255)`).

Todas são registradas em `app/api/v1/router.py`. As mensagens de 404 e
422 são em português.

## Frontend

### Rotas

| Rota                         | Componente                                  |
|------------------------------|---------------------------------------------|
| `/filmes/novo`               | `MovieFormPage` (cadastro)                  |
| `/filmes/:skMovieId/editar`  | `MovieFormPage` (edição)                    |

O React Router dá prioridade ao trecho fixo `novo` sobre `:skMovieId`, então
`/filmes/novo` não é confundido com um filme.

### Arquivos

| Arquivo                                   | Responsabilidade                                    | CAs |
|-------------------------------------------|-----------------------------------------------------|-----|
| `src/api/client.ts`                       | `apiSend(método, caminho, corpo)` para POST/PUT/DELETE; `ApiError` ganha `fieldErrors` (campo → mensagem) montado a partir do `422` | CA-14, CA-15 |
| `src/api/movies.ts`                       | `createMovie`, `updateMovie`, `deleteMovie`, `listGenres`, `searchDirectors` | — |
| `src/types/movie.ts`                      | `MovieInput`, `MovieStatus`                         | —   |
| `src/utils/movieForm.ts` (novo)           | Valores do formulário ↔ `MovieInput`; `validateMovieForm(valores) → erros por campo`, com as mesmas regras da API; ano máximo = ano atual + 10 | CA-6 a CA-13 |
| `src/hooks/useFlash.ts`                   | Contexto das mensagens de sucesso: `showFlash(texto)` | CA-31 |
| `src/components/FlashProvider.tsx`        | Guarda e mostra a mensagem no topo; some em 5 s ou ao fechar | CA-31 |
| `src/components/GenrePicker.tsx`          | Os 19 gêneros como caixas de seleção em etiquetas   | CA-2, CA-13 |
| `src/components/DirectorPicker.tsx`       | Campo com sugestões (debounce de 300 ms, a partir de 2 letras); Enter ou clique adiciona; etiquetas removíveis; marca "novo" quando o nome não veio de uma sugestão exata; ignora repetidos | CA-16 a CA-19 |
| `src/components/ConfirmDialog.tsx`        | Diálogo modal com `<dialog>` nativo: título, texto, confirmar e cancelar; Esc cancela | CA-26 |
| `src/pages/MovieFormPage.tsx`             | Cadastro ou edição (conforme a rota); carrega o filme na edição (`useMovie`); valida, envia, mostra erros do servidor nos campos; ao salvar, vai para os detalhes com `replace` e mensagem | CA-1 a CA-25, CA-32 |
| `src/pages/MovieDetailPage.tsx`           | Botões "Editar" e "Excluir"; confirmação com o número de avaliações; após excluir, mensagem e volta ao catálogo | CA-20, CA-26 a CA-30 |
| `src/pages/CatalogPage.tsx`               | Botão "Novo filme" no cabeçalho                     | CA-1 |
| `src/App.tsx`                             | Rotas novas; `FlashProvider` envolvendo as rotas    | —   |
| `.css` dos componentes e da página novos  | Formulário em duas colunas a partir de 640 px e uma abaixo | CA-33 |

### Comportamentos do formulário

- **Data e ano (CA-8):** ao escolher uma data, o ano é preenchido com o ano
  dela. Se o ano for mudado depois e divergir, aparece o erro no campo Ano.
- **Duração 0 de filme importado (D-7):** aparece vazia no formulário.
- **Erros:** aparecem ao sair de cada campo e todos de uma vez ao tentar
  salvar. O foco vai para o primeiro campo com erro.
- **Erros do servidor (`422`):** `fieldErrors` é associado aos campos pelo
  `loc`. Qualquer outro erro vira uma mensagem no topo do formulário, e os
  dados digitados continuam (CA-15).
- **Envio:** o botão "Salvar" fica desabilitado e mostra "Salvando…" até a
  resposta, o que impede duplo envio.
- **Depois de salvar:** `navigate("/filmes/<chave>", { replace: true })`.
  Assim o voltar do navegador não retorna ao formulário. O
  `state.catalogSearch` recebido é repassado, para o "Voltar ao catálogo" da
  002 continuar funcionando.

## Arquivos

| Arquivo                                                  | Ação    |
|----------------------------------------------------------|---------|
| `backend/app/movies/models.py`                           | Alterar (`DimPerson.nome_normalizado` + índice) |
| `backend/migrations/versions/0003_nome_normalizado_pessoas.py` | Criar |
| `backend/app/movies/schemas.py`                          | Alterar (`MovieInput`) |
| `backend/app/movies/service.py`                          | Alterar (5 funções novas) |
| `backend/app/movies/router.py`, `backend/app/api/v1/router.py` | Alterar |
| `backend/app/core/errors.py`, `backend/app/main.py`      | Criar / alterar (mensagens de 422 em português) |
| `backend/tests/test_movie_management_api.py`             | Criar   |
| `backend/tests/test_load_data.py`                        | Alterar (conferir `nome_normalizado` preenchido) |
| `frontend/src/**` (tabela acima)                         | Criar / alterar |
| `README.md`, `CLAUDE.md`                                 | Alterar (decisões, status, migração 0003, armadilhas) |

## Testes

### Backend (`tests/test_movie_management_api.py`)

| Teste                                                                 | CAs         |
|-----------------------------------------------------------------------|-------------|
| `POST` completo: 201, `id_filme` UUID4, título sem espaços nas pontas, gêneros e diretores ligados; o filme aparece na busca | CA-3, CA-4, CA-10 |
| `POST` mínimo (título, ano, status): detalhes sem avaliações, financeiro `null`, listas vazias | CA-5 |
| Diretor com nome exato reaproveitado (não cria pessoa); nome diferente cria; repetidos ignorados; "Alberto Rodriguez" com só "Alberto Rodríguez" existente cria novo | CA-17, CA-18 |
| Validações: título vazio ou só espaços; título com 501 caracteres; ano 1887 e ano atual + 11; data com ano divergente; duração 0 e 1001; status fora da lista; URL sem http; sinopse com 4.001; diretor com 256 caracteres → 422 com a mensagem em português no campo certo | CA-6 a CA-12, CA-19 |
| Gênero inexistente → 422                                              | CA-13       |
| `PUT`: campos atualizados; `titulo_normalizado` recalculado (a busca acha o título novo e não o antigo); roteiristas, elenco, produtoras, métricas e avaliações preservados | CA-21, CA-22 |
| `PUT` tirando um diretor: o vínculo some, e a pessoa continua em `dim_people` | CA-23 |
| `PUT` e `DELETE` de filme inexistente → 404                           | CA-25, CA-28 |
| `DELETE`: 204; avaliações, vínculos, métricas e resumo apagados; pessoas, gêneros e produtoras mantidos; `GET` do filme dá 404 | CA-27 a CA-29 |
| `GET /genres`: os gêneros em ordem alfabética                         | CA-2        |
| `GET /directors`: sem acentos; só `tipo_pessoa = "Diretor"`; no máximo 10; nome exato primeiro; termo de 1 caractere → 422 | CA-16 |
| `422` de `GET /movies?page=0` com a mensagem em português             | CA-14       |

A carga da 000 preenche `nome_normalizado` (teste em `test_load_data.py`).
A migração 0003 é testada ida, volta e ida de novo num banco temporário,
com `alembic check`, e depois aplicada no `moviestars.db`.

### Frontend

`build` e `lint`, e um roteiro Playwright contra uma **cópia** do
`moviestars.db` no scratchpad (DEC-12), para não deixar filmes e diretores
de teste no banco de desenvolvimento. O roteiro cobre:
- cadastro completo e mínimo;
- cada erro de validação na tela;
- sugestões de diretor e a marca "novo";
- edição com troca de título (a busca acha o título novo);
- cancelar a edição;
- exclusão com a contagem de avaliações e o cancelamento;
- mensagens de sucesso;
- API desligada ao salvar;
- duplo clique;
- 360 px.

### Com os dados reais

Tempo de `GET /directors` com termos curtos e longos, de `POST`, `PUT` e
`DELETE` (RNF-1), na cópia do banco.

## Decisões

- **DEC-1. REST com `POST`, `PUT` e `DELETE` em `/movies`, e rotas de
  leitura para gêneros e diretores.** Segue as convenções da constituição
  (seção 5.2: 201, 204, 404, 422).
- **DEC-2. `PUT` com o corpo completo.** O formulário sempre envia todos os
  campos editáveis, e o mesmo schema serve para criar e atualizar.
  *Descartado:* `PATCH` com campos parciais, que traz mais casos para validar
  sem ganho para esta tela.
- **DEC-3. Gêneros e diretores identificados pelo nome no corpo.** Os nomes
  são únicos no banco (restrições existentes), o que dá o "reaproveitar pelo
  nome exato" da D-3 da spec sem precisar de ids. Também deixa o formulário
  de edição ser preenchido com o `MovieDetail` da 002 sem mudá-lo.
  *Descartado:* enviar `sk_person_id`, que exigiria incluir os ids no
  detalhe e tratar dois formatos (id para existentes, nome para novos).
- **DEC-4. Coluna `nome_normalizado` em `dim_people`, com índice.** Com os
  dados reais: 5 ms contra 104 ms. É o mesmo mecanismo da 001, com o mesmo
  motivo para não mexer na carga.
  *Descartado:* função de normalização aplicada a cada consulta.
- **DEC-5. Remoção com `DELETE` direto, usando o `ON DELETE CASCADE` do
  banco.** O `PRAGMA foreign_keys=ON` já é ligado em `session.py`, e o teste
  confere que os dependentes somem.
  *Descartado:* `session.delete(movie)` do ORM, que carregaria avaliações,
  vínculos e métricas só para apagá-los.
- **DEC-6. A edição troca só os vínculos de diretores.** `people` também
  guarda roteiristas e atores, que a edição não toca (CA-22).
- **DEC-7. `titulo_normalizado` recalculado explicitamente no `PUT`.** O
  `default` só roda no insert (DEC-2 da 001).
- **DEC-8. Mensagens de validação da API em português,** por um tratador de
  `RequestValidationError` que traduz os tipos de erro do Pydantic e mantém
  o formato de resposta do FastAPI.
  *Descartado:* manter as mensagens em inglês, o que contraria a seção 5.1
  da constituição.
- **DEC-9. Mensagens de sucesso por um contexto React (`FlashProvider`).**
  A mensagem sobrevive à troca de página e não reaparece ao recarregar.
  *Descartado:* passar a mensagem no estado da navegação, que reapareceria a
  cada recarga da página.
- **DEC-10. Diálogo de confirmação com o `<dialog>` nativo do HTML.** Ele já
  vem com modal, foco e Esc, sem dependências.
  *Descartado:* `window.confirm`, que não permite o texto e os botões do
  CA-26. *Descartado:* bibliotecas de modal.
- **DEC-11. Uma página de formulário para cadastro e edição,** com a mesma
  validação no frontend (`validateMovieForm`) e no backend (Pydantic). O
  frontend avisa antes de enviar (CA-14), e o backend garante as regras.
- **DEC-12. O roteiro Playwright roda numa cópia do banco.** Criar e
  excluir filmes deixaria filmes e diretores de teste no `moviestars.db`.
  *Descartado:* rodar no banco de desenvolvimento e limpar depois, o que não
  apagaria os diretores criados.
- **DEC-13. Depois de salvar, a navegação substitui o formulário no
  histórico.** O voltar do navegador leva ao catálogo, e não de volta a um
  formulário já enviado.

## Riscos

- **Migração 0003 no `moviestars.db`:** preenche 424.656 pessoas. A
  estimativa é de alguns segundos, e o Alembic desfaz tudo se falhar.
- **Validação duplicada:** as regras existem no frontend e no backend. Os
  testes do backend são a referência, e o roteiro no navegador confere que a
  tela mostra as mesmas mensagens.
