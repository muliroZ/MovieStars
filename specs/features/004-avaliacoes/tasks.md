# 004 — Adicionar avaliações — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Concluído (2026-09-26)                                  |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**, e só é marcada `- [x]` quando
ela passa. Os comandos de backend rodam em `backend/` e os de frontend em
`frontend/`. "Build e lint passam" significa que `bun run build` e
`bun run lint` terminam sem erros. Os testes de backend ficam em
`tests/test_reviews_api.py` e usam `conftest.py` e `helpers.py`.

## Fase 0 — API (backend)

- [x] **T-01. Schema `ReviewInput`** (CA-4 a CA-6)
  - `nome` (sem espaços nas pontas, 1 a 120), `estrelas` (inteiro de 1 a 5),
    `comentario` (sem espaços nas pontas, 1 a 1.000).
  - Testes chamando o schema:
    - valores válidos, com os espaços das pontas removidos;
    - nome vazio, só espaços ou com 121 caracteres;
    - estrelas ausentes, 0, 6, 4.5 e "abc";
    - comentário vazio ou com 1.001 caracteres.
  - Verificação: `pytest` e `ruff check .` passam.

- [x] **T-02. `create_review` e `POST /movies/{sk_movie_id}/reviews`** (CA-7, CA-9 a CA-14)
  - `_to_nota` ao lado do `_to_stars`.
  - `create_review`: confere o filme, grava com `nota = estrelas × 2`, faz
    `commit` e `refresh` e devolve o `ReviewItem`.
  - Rota com status 201 e 404 "Filme não encontrado.".
  - Testes pelo `client`:
    - 201 com `estrelas` 4.0 e `created_at` terminando em `Z`;
    - no banco, `nota` = 8.0;
    - a avaliação nova vem primeiro em `GET /reviews`, e o total sobe;
    - `media_estrelas` e `qtd_avaliacoes` mudam no detalhe e no catálogo;
    - na primeira avaliação, a média deixa de ser `null`;
    - filme Planejado aceita avaliação;
    - campos inválidos dão 422 com a mensagem em português no campo certo;
    - filme inexistente dá 404;
    - `dim_reviews` não muda.
  - Verificação: `pytest`, `ruff check .` e `ruff format --check .` passam.

- [x] **T-03. Desempenho numa cópia do banco** (RNF-1)
  - Medir o `POST` de avaliação (5 vezes) num filme com avaliações e num
    sem, numa cópia do `moviestars.db` no scratchpad.
  - Anotar os tempos na seção "Riscos" do plan e apagar a cópia.
  - Verificação: abaixo de 1 s; o `moviestars.db` não muda.

## Fase 1 — Base do frontend

- [x] **T-04. Tipo, chamada à API e `utils/reviewForm.ts`** (CA-4 a CA-6)
  - `ReviewInput` em `types/movie.ts`; `createReview` em `api/movies.ts`.
  - `reviewForm.ts`: valores iniciais, `validateReviewForm` com as mesmas
    regras e mensagens da API e conversão para o corpo do `POST`.
  - Verificação:
    - build e lint passam;
    - um script temporário com `bun` roda os mesmos casos da T-01 e compara
      com a validação do backend, e as mensagens batem em todos.

- [x] **T-05. `useMovie.refresh()` e `useMovieReviews.reload()`** (CA-10 a CA-12, DEC-5)
  - `refresh`: busca de novo e mantém os dados atuais até a resposta; se
    falhar, os dados antigos continuam.
  - `reload`: busca a página 1 e substitui a lista sem passar por
    "carregando".
  - O `retry()` continua igual.
  - Verificação: build e lint passam, sem avisos das regras de hooks; o
    roteiro da 002 (`check_detail.py`) continua 40/40.

## Fase 2 — Componentes

- [x] **T-06. `StarInput`** (CA-2, CA-15, DEC-7)
  - 5 botões de opção nativos, visualmente escondidos, com as estrelas como
    rótulos.
  - Prévia ao passar o mouse; nenhuma marcada de início; nomes acessíveis
    "N de 5 estrelas"; área de toque de pelo menos 44 px; estado de erro.
  - Verificação: build e lint passam; conferido na T-09.

- [x] **T-07. `ReviewForm`** (CA-1 a CA-10, CA-14)
  - Título "Adicionar avaliação"; Nome, Nota e Comentário com o contador
    "N/1000"; erros ao sair do campo e ao enviar, com foco no primeiro.
  - Botão "Enviar avaliação", que mostra "Enviando…", com proteção contra
    duplo clique.
  - Erro geral no topo do formulário (422, 404, rede).
  - Ao salvar: limpa os campos, mostra "Avaliação adicionada." e chama
    `onCreated`.
  - Verificação: build e lint passam; conferido na T-09.

## Fase 3 — Integração na página

- [x] **T-08. Formulário na página de detalhes** (CA-1, CA-10 a CA-12, CA-15, DEC-6)
  - `ReviewList` com a propriedade `form`; `MovieDetailPage` passa o
    `ReviewForm`, e o `onCreated` chama `refresh()` e `reload()`.
  - Estilos: campos empilhados; estrelas grandes em 360 px.
  - Verificação: build e lint passam; com a API numa cópia do banco, uma
    avaliação enviada aparece no topo, e a média do topo muda sem a página
    piscar.

## Fase 4 — Verificação e fechamento

- [x] **T-09. Roteiro no navegador numa cópia do banco** (CA-1 a CA-15, DEC-9)
  - Script Playwright (no scratchpad) cobrindo os itens da seção "Testes" do
    plan. Rodar também os roteiros das features 001 a 003.
  - Anotar os resultados aqui e apagar a cópia.
  - Verificação: todos os itens ok, com os problemas encontrados corrigidos
    antes de marcar; o `moviestars.db` não muda.
  - **Resultado (2026-09-26):** API apontada para uma cópia do
    `moviestars.db`. **145 de 145 verificações ok**, na primeira rodada.

    | Roteiro | Resultado |
    |---|---|
    | `check_catalog.py` (001) | 34/34 |
    | `check_catalog_extra.py` (001) | 8/8 |
    | `check_detail.py` (002) | 40/40 |
    | `check_reviews.py` (004) | 24/24 |
    | `check_manage.py` (003) | 39/39 |

    `check_reviews.py` cobre:
    - o formulário acima da lista, sem estrela marcada;
    - os três obrigatórios com foco no primeiro, e nome e comentário só com
      espaços recusados;
    - a prévia das estrelas ao passar o mouse, o clique, a seta do teclado e
      o nome acessível "4 de 5 estrelas";
    - o contador "3/1000";
    - o envio com a lista expandida: um único `POST` num duplo clique; a nova
      no topo com 5,0 estrelas e a data; a lista de volta às 10 mais
      recentes; o total e a média do topo atualizados; a página sem voltar a
      "Carregando filme…"; o formulário limpo; "Avaliação adicionada.";
    - a primeira avaliação de um filme sem avaliações;
    - um filme Planejado aceitando avaliação;
    - a API fora do ar mantendo os dados;
    - um filme removido depois de aberto: "Filme não encontrado.";
    - 360 px, com as estrelas de 44 px.

    O `moviestars.db` terminou igual (95.645 filmes, 424.656 pessoas e
    43.666 avaliações), e a cópia foi apagada.

- [x] **T-10. Documentação** (constituição, seção 6)
  - `README.md`: decisões da 004 e status. Com a 004, as quatro features
    principais estão concluídas.
  - `CLAUDE.md`:
    - mapa com os arquivos novos;
    - armadilhas: `_to_nota`/`_to_stars` como únicas conversões de escala;
      validação espelhada em `reviewForm.ts`; `refresh`/`reload` em vez de
      `retry` para atualizar sem piscar.
  - Verificação: os caminhos citados existem.

- [x] **T-11. Definição de pronto** (constituição, seção 6)
  - Backend: `pytest`, `ruff check .`, `ruff format --check .` e
    `alembic check` passam.
  - Frontend: `bun run build` e `bun run lint` passam.
  - CA-1 a CA-15 conferidos contra os testes, a T-03 e a T-09.
  - Status da spec, do plan e das tasks atualizado para concluído.
  - Verificação: saídas dos comandos no resumo final.

## Rastreabilidade

| CA    | Tasks                   |
|-------|-------------------------|
| CA-1  | T-07, T-08, T-09        |
| CA-2  | T-06, T-09              |
| CA-3  | T-07, T-09              |
| CA-4  | T-01, T-04, T-07        |
| CA-5  | T-01, T-04, T-07        |
| CA-6  | T-01, T-04, T-07        |
| CA-7  | T-02, T-07, T-09        |
| CA-8  | T-07, T-09              |
| CA-9  | T-02                    |
| CA-10 | T-02, T-05, T-07, T-08  |
| CA-11 | T-02, T-05, T-08        |
| CA-12 | T-02, T-05, T-08        |
| CA-13 | T-02                    |
| CA-14 | T-02, T-07, T-09        |
| CA-15 | T-06, T-08, T-09        |
| RNF-1 | T-03                    |
