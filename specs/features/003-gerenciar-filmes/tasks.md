# 003 — Gerenciar filmes — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Em revisão                                              |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos de backend rodam em `backend/` e os de frontend em
`frontend/`. "Build e lint passam" significa que `bun run build` e
`bun run lint` terminam sem erros. Os testes de backend ficam em
`tests/test_movie_management_api.py`, salvo indicação, e usam
`conftest.py` e `helpers.py`.

## Fase 0 — Base do backend

- [ ] **T-01. `nome_normalizado` em `dim_people` e migração 0003** (CA-16, DEC-4)
  - `models.py`: coluna com `default` calculado a partir de `nome_pessoa` e
    `server_default=""`; índice `ix_dim_people_tipo_nome_normalizado`.
  - Migração `0003_nome_normalizado_pessoas.py`: coluna, preenchimento em
    lotes com cópia própria da normalização, índice; `downgrade` desfaz.
  - Testes:
    - uma pessoa inserida pelo ORM recebe `nome_normalizado`;
    - em `test_load_data.py`, a carga preenche a coluna (ex.: `"F. Javier
      Gutiérrez"` vira `"f. javier gutierrez"`).
  - Verificação:
    - `pytest` passa;
    - num banco temporário, `alembic upgrade head`, depois `downgrade -1` e
      de novo `upgrade head` rodam sem erro, e as pessoas inseridas antes
      da 0003 ficam preenchidas;
    - `alembic check` não detecta diferenças.

- [ ] **T-02. Aplicar a migração 0003 no `moviestars.db`**
  - Verificação:
    - `alembic current` mostra `0003_nome_normalizado_pessoas (head)`;
    - nenhuma pessoa tem `nome_normalizado` vazio;
    - `EXPLAIN QUERY PLAN` da busca de diretores usa o índice novo.

- [ ] **T-03. Mensagens de validação em português** (CA-14, DEC-8)
  - `app/core/errors.py` com o tratador de `RequestValidationError`;
    registro em `create_app`.
  - Testes:
    - `GET /movies?page=0` dá 422 com a mensagem "Deve ser no mínimo 1.";
    - o formato `detail[].loc/msg/type` é mantido.
  - Verificação: `pytest` passa, inclusive os testes da 001 e da 002.

## Fase 1 — API de gerenciamento

- [ ] **T-04. `GET /genres` e `GET /directors`** (CA-2, CA-13, CA-16)
  - `list_genres` e `search_directors` no serviço; `genres_router` e
    `directors_router`, registrados em `app/api/v1/router.py`.
  - Testes:
    - gêneros em ordem alfabética;
    - "rodri" encontra "Alberto Rodríguez" e "Alberto Rodriguez";
    - só pessoas do tipo Diretor;
    - no máximo 10 resultados;
    - o nome exato vem primeiro;
    - `%` como texto comum;
    - termo de 1 caractere dá 422.
  - Verificação: `pytest` e `ruff check .` passam.

- [ ] **T-05. Schema `MovieInput` e validações** (CA-6 a CA-12, CA-19)
  - Regras da tabela do plan, com mensagens em português nos validadores
    próprios (data e ano; URL).
  - Testes chamando o schema:
    - cada regra com um valor válido e um inválido;
    - título com espaços nas pontas é limpo;
    - sinopse e URL vazias viram `None`;
    - gêneros e diretores repetidos são removidos;
    - o limite do ano segue o ano atual + 10.
  - Verificação: `pytest` passa.

- [ ] **T-06. `POST /api/v1/movies`** (CA-3 a CA-5, CA-13, CA-14, CA-17, CA-18)
  - `create_movie`:
    - confere os gêneros;
    - resolve os diretores (nome exato reaproveita, os outros são criados);
    - gera `id_filme = str(uuid4())`;
    - faz `commit` e devolve `get_movie`.
  - Rota com status 201.
  - Testes:
    - cadastro completo: 201, `id_filme` UUID4, gêneros e diretores ligados,
      e o filme aparece em `GET /movies?search=`;
    - cadastro mínimo: sem avaliações, `financeiro` `null` e listas vazias;
    - diretor existente reaproveitado, sem pessoa nova em `dim_people`;
    - nome diferente cria um diretor;
    - "Alberto Rodriguez" cria um diretor novo quando só existe "Alberto
      Rodríguez";
    - gênero inexistente dá 422 no campo `generos`;
    - campos inválidos dão 422 com a mensagem em português no `loc` certo.
  - Verificação: `pytest` e `ruff check .` passam.

- [ ] **T-07. `PUT /api/v1/movies/{sk_movie_id}`** (CA-21 a CA-23, CA-25)
  - `update_movie`:
    - atualiza os campos;
    - recalcula `titulo_normalizado`;
    - troca os gêneros e só os diretores;
    - faz `commit` e devolve `get_movie`.
  - Testes:
    - campos atualizados;
    - a busca acha o título novo e não o antigo;
    - roteiristas, elenco, produtoras, métricas e avaliações preservados;
    - diretor retirado: o vínculo some e a pessoa continua;
    - filme inexistente dá 404;
    - corpo inválido dá 422.
  - Verificação: `pytest` e `ruff check .` passam.

- [ ] **T-08. `DELETE /api/v1/movies/{sk_movie_id}`** (CA-27 a CA-29)
  - `delete_movie` com `DELETE` direto e a cascata do banco; rota com 204.
  - Testes:
    - 204 sem corpo;
    - avaliações, vínculos (gênero, pessoa, produtora), métricas e resumo
      apagados;
    - pessoas, gêneros e produtoras mantidos;
    - `GET` do filme dá 404 depois;
    - filme inexistente dá 404.
  - Verificação: `pytest` e `ruff check .` passam.

- [ ] **T-09. Desempenho numa cópia do banco** (RNF-1, DEC-12)
  - Copiar o `moviestars.db` para o scratchpad e medir:
    - `GET /directors` com "an", "rodri" e um nome completo;
    - `POST`, `PUT` e `DELETE` de um filme com 3 gêneros e 2 diretores.
  - Anotar os tempos na seção "Riscos" do plan e apagar a cópia depois.
  - Verificação: todos abaixo de 1 s; o `moviestars.db` não muda (contagem
    de filmes e pessoas igual antes e depois).

## Fase 2 — Base do frontend

- [ ] **T-10. Cliente, tipos e chamadas à API** (CA-14, CA-15)
  - `client.ts`: `apiSend(método, caminho, corpo)`, tratando 204 sem corpo;
    `ApiError.fieldErrors` montado a partir do `detail` do 422 (campo →
    mensagem).
  - `types/movie.ts`: `MovieInput` e `MovieStatus`.
  - `movies.ts`: `createMovie`, `updateMovie`, `deleteMovie`, `listGenres` e
    `searchDirectors`.
  - Verificação: build e lint passam, sem `any`.

- [ ] **T-11. `utils/movieForm.ts`** (CA-6 a CA-13, CA-19)
  - Valores do formulário ↔ `MovieInput` (duração 0 importada vira vazio);
    `validateMovieForm`, com as mesmas regras e mensagens da API.
  - Verificação: build e lint passam. Um script temporário com `bun` (fora
    do projeto) confere:
    - cada regra com valor válido e inválido;
    - a data preenchendo o ano;
    - a conversão ida e volta de um `MovieDetail`.

- [ ] **T-12. Mensagens de sucesso (`useFlash` e `FlashProvider`)** (CA-31, DEC-9)
  - Contexto com `showFlash(texto)`; a mensagem aparece no topo, com botão
    de fechar, e some em 5 s. O `FlashProvider` envolve as rotas em
    `App.tsx`.
  - Verificação: build e lint passam, sem avisos das regras de hooks nem do
    React Refresh.

## Fase 3 — Componentes do formulário

- [ ] **T-13. `GenrePicker`** (CA-2, CA-13)
  - Os gêneros vindos de `GET /genres`, como caixas de seleção em
    etiquetas; seleção múltipla; estado de carregamento e erro.
  - Verificação: build e lint passam; conferido na T-20.

- [ ] **T-14. `DirectorPicker`** (CA-16 a CA-19)
  - O campo tem:
    - sugestões a partir de 2 letras, com debounce de 300 ms;
    - navegação pelas sugestões com as setas, e adição com Enter ou clique;
    - etiquetas removíveis;
    - a marca "novo" quando o nome não corresponde exatamente a uma
      sugestão;
    - repetidos ignorados;
    - erro de nome longo.
  - Verificação: build e lint passam; conferido na T-20.

- [ ] **T-15. `ConfirmDialog`** (CA-26, DEC-10)
  - `<dialog>` nativo com título, texto, botões confirmar e cancelar, e Esc
    para cancelar; o botão de confirmar fica desabilitado durante a ação.
  - Verificação: build e lint passam; conferido na T-20.

## Fase 4 — Páginas

- [ ] **T-16. Cadastro: `MovieFormPage` e botão "Novo filme"** (CA-1 a CA-15, CA-31)
  - Rota `/filmes/novo`; botão "Novo filme" no cabeçalho do catálogo.
  - O formulário:
    - valida ao sair de cada campo e tudo de uma vez ao salvar, com foco no
      primeiro erro;
    - mostra os erros do servidor nos campos;
    - desabilita o botão enquanto salva;
    - depois de salvar, vai para os detalhes com `replace` e mostra "Filme
      cadastrado.".
  - Verificação: build e lint passam; com a API (na cópia do banco), um
    filme cadastrado abre nos detalhes com a mensagem.

- [ ] **T-17. Edição** (CA-20 a CA-25, CA-32)
  - Rota `/filmes/:skMovieId/editar`; botão "Editar" nos detalhes.
  - Formulário preenchido a partir de `useMovie`; "Cancelar" volta aos
    detalhes; carregando, erro com "Tentar novamente" e "Filme não
    encontrado"; 404 ao salvar mostra "Filme não encontrado"; depois de
    salvar, "Filme atualizado.". O `catalogSearch` é repassado.
  - Verificação: build e lint passam; conferido na T-20.

- [ ] **T-18. Remoção** (CA-26 a CA-30)
  - Botão "Excluir" nos detalhes; `ConfirmDialog` com o título e a
    quantidade de avaliações (sem essa frase quando não houver avaliações).
  - Ao confirmar, `deleteMovie`, a mensagem "Filme excluído." e a volta ao
    catálogo (mesma busca e página, se houver). Em caso de falha, a
    mensagem de erro aparece no diálogo.
  - Verificação: build e lint passam; conferido na T-20.

- [ ] **T-19. Layout responsivo** (CA-33)
  - Formulário em duas colunas a partir de 640 px e uma abaixo; diálogo com
    largura máxima e margens em 360 px.
  - Verificação: 360, 768 e 1280 px sem rolagem horizontal no formulário e
    no diálogo.

## Fase 5 — Verificação e fechamento

- [ ] **T-20. Roteiro no navegador numa cópia do banco** (CA-1 a CA-33, DEC-12)
  - Script Playwright (no scratchpad) com a API apontada para a cópia do
    `moviestars.db`, cobrindo os itens da seção "Testes" do plan. Rodar
    também os roteiros da 001 e da 002.
  - Anotar os resultados aqui e apagar a cópia depois.
  - Verificação: todos os itens ok, com os problemas encontrados corrigidos
    antes de marcar; o `moviestars.db` não muda.

- [ ] **T-21. Documentação** (constituição, seção 6)
  - `README.md`: decisões da 003, a migração 0003 em "Depois de atualizar o
    repositório" e o status.
  - `CLAUDE.md`:
    - mapa com os arquivos novos;
    - armadilhas: `nome_normalizado` só no insert; a edição troca apenas os
      diretores em `people`; remoção pela cascata do banco; mensagens de
      422 traduzidas em `core/errors.py`.
  - Verificação: os caminhos e comandos citados existem.

- [ ] **T-22. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .`, `ruff format --check .` e
    `alembic check` passam.
  - Frontend: `bun run build` e `bun run lint` passam.
  - CA-1 a CA-33 conferidos contra os testes, a T-09 e a T-20.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                         |
|-------|-------------------------------|
| CA-1  | T-16, T-20                    |
| CA-2  | T-04, T-13, T-16              |
| CA-3  | T-06, T-16                    |
| CA-4  | T-06, T-20                    |
| CA-5  | T-06, T-20                    |
| CA-6  | T-05, T-11, T-16              |
| CA-7  | T-05, T-11, T-16              |
| CA-8  | T-05, T-11, T-16              |
| CA-9  | T-05, T-11, T-16              |
| CA-10 | T-05, T-11, T-16              |
| CA-11 | T-05, T-11, T-16              |
| CA-12 | T-05, T-11, T-16              |
| CA-13 | T-04, T-06, T-11, T-13        |
| CA-14 | T-03, T-06, T-10, T-16        |
| CA-15 | T-10, T-16, T-20              |
| CA-16 | T-01, T-04, T-14              |
| CA-17 | T-06, T-14                    |
| CA-18 | T-05, T-06, T-14              |
| CA-19 | T-05, T-11, T-14              |
| CA-20 | T-17, T-20                    |
| CA-21 | T-07, T-17                    |
| CA-22 | T-07                          |
| CA-23 | T-07                          |
| CA-24 | T-17, T-20                    |
| CA-25 | T-07, T-17                    |
| CA-26 | T-15, T-18                    |
| CA-27 | T-08, T-18                    |
| CA-28 | T-08, T-18, T-20              |
| CA-29 | T-08                          |
| CA-30 | T-18, T-20                    |
| CA-31 | T-12, T-16, T-17, T-18        |
| CA-32 | T-17, T-20                    |
| CA-33 | T-19, T-20                    |
| RNF-1 | T-09                          |
