# 004 — Adicionar avaliações — Plan

| Campo       | Valor                                                 |
|-------------|-------------------------------------------------------|
| Status      | Concluído                                             |
| Spec        | [`spec.md`](spec.md) (aprovada)                       |
| Referências | `specs/constitution.md` (seções 4.1, 4.2, 5.2, 5.3, 6); plans da 002 e da 003 |

## Visão geral

```text
MovieDetailPage
 ├─ topo: média geral ◄──────────── useMovie.refresh() (sem voltar a "carregando")
 └─ ReviewList
     ├─ título "Avaliações (N)"
     ├─ ReviewForm ── POST /api/v1/movies/{id}/reviews ── 201 ─┐
     │    (nome, StarInput, comentário)                        │ "Avaliação adicionada."
     └─ lista ◄──────────────────── useMovieReviews.reload() ◄─┘ (10 mais recentes)
```

## Backend

### `POST /api/v1/movies/{sk_movie_id}/reviews`

Corpo (`ReviewInput`):

```json
{ "nome": "Ana Souza", "estrelas": 4, "comentario": "Ótimo filme." }
```

| Campo        | Regra (422 se falhar, mensagens em português)                   | CA   |
|--------------|-----------------------------------------------------------------|------|
| `nome`       | sem espaços nas pontas; 1 a 120 caracteres                      | CA-4 |
| `estrelas`   | inteiro de 1 a 5; `4.5`, `0`, `6` e texto são recusados         | CA-5 |
| `comentario` | sem espaços nas pontas; 1 a 1.000 caracteres                    | CA-6 |

Respostas:
- `201` com o `ReviewItem` da 002 (`sk_movie_review_id`, `nome`, `estrelas`,
  `comentario`, `created_at` com `Z`);
- `404` com "Filme não encontrado." (CA-14);
- `422` com as mensagens em português do tratador da 003 (CA-7).

### Serviço (`app/movies/service.py`)

`create_review(db, sk_movie_id, dados) -> ReviewItem | None`:

1. confere se o filme existe (senão `None` → 404);
2. cria `MovieReview(sk_movie_id, nome, nota=_to_nota(estrelas), comentario)`;
3. `commit` e `refresh`, para ler o `created_at`, que o banco preenche
   (DEC-3);
4. devolve `_to_review_item(review)`, que converte a nota de volta para
   estrelas com o `_to_stars` de sempre.

`_to_nota(estrelas) = estrelas * 2` fica ao lado do `_to_stars`: são as duas
únicas conversões de escala, e as duas ficam no serviço (constituição, seção
4.1; DEC-2).

O `dim_reviews` não é tocado (spec, "Consequências conhecidas").

### Arquivos do backend

| Arquivo                                   | Ação                               |
|-------------------------------------------|------------------------------------|
| `app/movies/schemas.py`                   | `ReviewInput`                      |
| `app/movies/service.py`                   | `create_review`, `_to_nota`        |
| `app/movies/router.py`                    | rota `POST /{sk_movie_id}/reviews` |
| `tests/test_reviews_api.py`               | criar                              |

## Frontend

### Atualização sem piscar (DEC-5)

Depois de salvar, a média no topo e a lista precisam refletir a avaliação
nova. Hoje, os `retry()` de `useMovie` e `useMovieReviews` voltam ao estado
"carregando". Com eles, a página inteira trocaria por "Carregando filme…" e
o formulário seria desmontado. Então:

- **`useMovie.refresh()`** (novo): busca o filme de novo e **mantém os dados
  atuais na tela** até a resposta chegar. Se a atualização falhar, os dados
  antigos continuam.
- **`useMovieReviews.reload()`** (novo): busca de novo a página 1 e substitui
  a lista, sem passar por "carregando". Isso também desfaz o "Mostrar mais"
  (D-5 da spec).

O `retry()` continua como está, para as telas de erro.

### Componentes e arquivos

| Arquivo                             | Responsabilidade                                     | CAs |
|-------------------------------------|------------------------------------------------------|-----|
| `src/types/movie.ts`                | `ReviewInput`                                        | —   |
| `src/api/movies.ts`                 | `createReview(skMovieId, input)`                     | —   |
| `src/utils/reviewForm.ts` (novo)    | Valores do formulário e `validateReviewForm`, com as mesmas regras e mensagens da API (como `movieForm.ts` na 003) | CA-4 a CA-6 |
| `src/components/StarInput.tsx` (novo) | 5 estrelas como botões de opção (`input type="radio"`) visualmente escondidos: as setas do teclado e os leitores de tela funcionam sem código extra (DEC-7); prévia ao passar o mouse; nenhuma marcada de início; rótulos "N de 5 estrelas"; área de toque de pelo menos 44 px | CA-2, CA-15 |
| `src/components/ReviewForm.tsx` (novo) | Título "Adicionar avaliação"; Nome, Nota (`StarInput`) e Comentário com o contador "N/1000"; erros por campo; botão "Enviar avaliação", que mostra "Enviando…" e barra o duplo clique; erro geral no topo do formulário; ao salvar: limpa, chama `onCreated` e mostra a mensagem | CA-1 a CA-10, CA-14 |
| `src/components/ReviewList.tsx`     | Nova propriedade `form` (ReactNode), exibida entre o título e a lista (DEC-6) | CA-1 |
| `src/hooks/useMovie.ts`             | `refresh()`                                          | CA-11 |
| `src/hooks/useMovieReviews.ts`      | `reload()`                                           | CA-10, CA-12 |
| `src/pages/MovieDetailPage.tsx`     | Passa o `ReviewForm` para o `ReviewList`; `onCreated` chama `refresh()` e `reload()` | CA-10 a CA-12 |
| `.css` dos componentes novos        | Estrelas grandes; campos empilhados                  | CA-15 |

### Comportamentos do formulário

- **Erros:** aparecem ao sair de cada campo e todos juntos ao tentar enviar,
  com foco no primeiro campo com erro (o mesmo padrão da 003).
- **Sucesso:**
  - `showFlash("Avaliação adicionada.")`;
  - os campos voltam ao estado inicial (nenhuma estrela marcada);
  - `onCreated()` atualiza a média e a lista.
- **Falhas:**
  - `422`: os erros aparecem nos campos, e o topo mostra "Alguns campos estão
    inválidos.";
  - `404`: "Filme não encontrado.";
  - rede ou servidor: a mensagem do `ApiError`, e os dados digitados continuam
    no formulário (CA-8);
  - erro inesperado fora da API: "Não foi possível enviar a avaliação."
    (texto aprovado na fase 2).

## Testes

### Backend (`tests/test_reviews_api.py`)

| Teste                                                                   | CAs          |
|-------------------------------------------------------------------------|--------------|
| `POST` válido: 201; `estrelas` 4.0; nome e comentário sem espaços nas pontas; `created_at` com `Z`; no banco, `nota` = 8.0 | CA-9 |
| A avaliação nova aparece primeiro em `GET /reviews`; o total sobe; `media_estrelas` e `qtd_avaliacoes` mudam no detalhe e no catálogo | CA-10, CA-11 |
| Primeira avaliação de um filme sem avaliações: média deixa de ser `null` | CA-12 |
| Filme com status Planejado aceita avaliação                             | CA-13        |
| Validações: nome vazio, só espaços ou com 121 caracteres; estrelas ausentes, 0, 6, 4.5 e "abc"; comentário vazio ou com 1.001 caracteres → 422 com a mensagem em português no campo certo | CA-4 a CA-7 |
| Filme inexistente → 404 com "Filme não encontrado."                     | CA-14        |
| `dim_reviews` não muda                                                  | —            |

### Frontend

`build` e `lint`, e um roteiro Playwright numa **cópia** do `moviestars.db`
(como na 003, porque o roteiro grava avaliações). Ele cobre:
- erros de cada campo;
- estrelas pelo mouse e pelo teclado;
- o contador de caracteres;
- envio com a avaliação no topo, o total +1, a média atualizada e a
  mensagem;
- a primeira avaliação de um filme sem avaliações;
- a lista expandida voltando às 10 mais recentes;
- o duplo clique;
- a API fora do ar ao enviar;
- um filme removido entre abrir e enviar;
- 360 px;
- e as regressões das features 001 a 003.

### Com os dados reais

Tempo do `POST` na cópia do banco (RNF-1).

## Decisões

- **DEC-1. `POST /movies/{sk_movie_id}/reviews`,** como recurso filho do
  filme, ao lado do `GET` da 002; responde `201` com o mesmo `ReviewItem`.
- **DEC-2. A conversão de estrelas para nota (`_to_nota`) fica no serviço,**
  junto do `_to_stars` (constituição, seção 4.1).
  *Descartado:* converter no frontend ou no schema.
- **DEC-3. `refresh` depois do `commit` para obter o `created_at`,** que é
  preenchido pelo banco (`server_default`).
  *Descartado:* gerar a data em Python, o que criaria dois relógios (o da
  aplicação e o do banco) para o mesmo campo.
- **DEC-4. `estrelas: int` com `ge=1, le=5` no Pydantic.** Ele já recusa
  `4.5` (`int_from_float`) e texto, e o tratador da 003 já traduz essas
  mensagens.
- **DEC-5. Atualização silenciosa da média e da lista (`refresh`/`reload`)**
  em vez de voltar ao estado "carregando".
  *Descartado:* `retry()`, que faria a página piscar e desmontaria o
  formulário. *Descartado:* calcular a média nova no frontend, porque a média
  tem uma fonte só, o `AVG` no banco (constituição, seção 4.2).
- **DEC-6. O formulário entra no `ReviewList` por uma propriedade `form`.** O
  `ReviewList` continua só exibindo, e a página decide o que colocar entre o
  título e a lista.
- **DEC-7. `StarInput` com botões de opção nativos.** Setas do teclado, foco e
  leitores de tela funcionam sem código próprio.
  *Descartado:* botões comuns com o teclado tratado à mão.
- **DEC-8. Validação espelhada em `utils/reviewForm.ts`,** com as mesmas
  mensagens da API, como na 003 (e a mesma armadilha: mudou uma, mude a
  outra).
- **DEC-9. Roteiro Playwright numa cópia do banco,** porque ele grava
  avaliações (DEC-12 da 003).
- **DEC-10. Nenhuma dependência nova.**

## Riscos

- **RNF-1: confirmado na T-03 (2026-09-26),** numa cópia do `moviestars.db`
  (o original não mudou). Pior tempo do `POST` de avaliação em 5 execuções:
  37 ms num filme com 13 avaliações e 5 ms num filme sem avaliações.
- **Duas requisições depois de salvar** (detalhe e avaliações): são leituras
  pequenas (medidas na 002 entre 2 e 51 ms), sem impacto perceptível.
