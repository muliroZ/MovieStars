# 004 — Adicionar avaliações

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Concluída                                              |
| Depende de     | 002 (página de detalhes e lista de avaliações)         |
| Bloqueia       | —                                                      |
| Referências    | `specs/constitution.md` (seções 1, 4.1, 4.2, 5.2, 5.3) |

## Contexto

A página de detalhes (feature 002) mostra a média geral e a lista de
avaliações, mas não há como registrar uma avaliação nova. Esta feature
adiciona um formulário na seção de avaliações para gravar uma nota de 1 a 5
estrelas com uma resenha.

A constituição já define a escala (seção 4.1): a entrada é em **estrelas
inteiras de 1 a 5**, e o banco guarda `nota = estrelas × 2` (0 a 10). Ela
também define que a média é sempre calculada a partir das avaliações
individuais (seção 4.2), então uma avaliação nova já entra na média.

## Histórias de usuário

- **H-1.** Como administrador, quero registrar a avaliação de uma pessoa
  (nome, nota e resenha) na página do filme, para que ela conte na média.
- **H-2.** Como administrador, quero ver a avaliação nova na lista e a média
  atualizada logo depois de salvar, para confirmar que deu certo.
- **H-3.** Como administrador, quero ser avisado de erros antes de enviar,
  para não gravar avaliações incompletas.

## Critérios de aceitação

### Formulário

- **CA-1** (H-1). Na página de detalhes, a seção de avaliações tem um
  formulário "Adicionar avaliação" acima da lista (D-1), com três campos
  obrigatórios:
  - **Nome** de quem avalia (D-2);
  - **Nota**, de 1 a 5 estrelas;
  - **Comentário** (a resenha).
- **CA-2** (H-1). A nota é escolhida clicando numa das 5 estrelas. Ao passar
  o mouse, as estrelas mostram a nota que seria escolhida. A escolha também
  funciona pelo teclado (setas) e é anunciada para leitores de tela (ex.:
  "4 de 5 estrelas"). Não existe meia estrela na entrada (constituição,
  seção 4.1). Nenhuma estrela vem marcada de início (D-7).
- **CA-3** (H-1). O campo de comentário mostra quantos caracteres foram
  usados do limite (ex.: "42/1000") (D-8).

### Validação

- **CA-4** (H-3). **Nome:** obrigatório, de 1 a 120 caracteres depois de tirar
  os espaços do início e do fim (D-9).
- **CA-5** (H-3). **Nota:** obrigatória, inteiro de 1 a 5.
- **CA-6** (H-3). **Comentário:** obrigatório, de 1 a 1.000 caracteres
  depois de tirar os espaços do início e do fim (D-4).
- **CA-7** (H-3). Cada erro aparece junto do campo, em português, e a
  avaliação não é enviada enquanto houver erro. As mesmas regras valem na
  API, mesmo que a interface seja contornada, com as mensagens em português
  (constituição, seção 5.2; spec 003, DEC-8).
- **CA-8** (H-3). Enquanto a avaliação é salva, o botão fica desabilitado, e
  um duplo clique não grava duas avaliações. Se o salvamento falhar (API
  fora do ar, erro no servidor), aparece uma mensagem, e o que foi digitado
  continua no formulário.

### Resultado

- **CA-9** (H-1). A nota é gravada como `estrelas × 2` (ex.: 4 estrelas →
  nota 8) e exibida de volta como estrelas (4,0) (constituição, seção 4.1).
- **CA-10** (H-2). Depois de salvar:
  - a avaliação nova aparece no topo da lista, com o nome, as estrelas, o
    comentário e a data de hoje;
  - o formulário é limpo;
  - aparece a mensagem "Avaliação adicionada." (D-6).
- **CA-11** (H-2). O total da seção ("Avaliações (N)") e a média geral com a
  quantidade, no topo da página, são atualizados na hora. O cartão do filme
  no catálogo mostra a média nova na próxima vez que o catálogo for aberto.
- **CA-12** (H-2). Num filme sem avaliações, a primeira avaliação substitui
  "Este filme ainda não tem avaliações." e "Sem avaliações" pela lista e pela
  média.
- **CA-13** (H-1). Qualquer filme pode receber avaliações, seja qual for o
  status (D-3).
- **CA-14** (H-1). Se o filme tiver sido removido (por exemplo, em outra
  aba), salvar mostra a mensagem "Filme não encontrado.".

### Layout

- **CA-15**. O formulário é utilizável a partir de 360 px de largura, sem
  rolagem horizontal, e as estrelas continuam fáceis de tocar.

## Casos de borda

| Situação                                                  | Comportamento esperado                                    |
|-----------------------------------------------------------|-----------------------------------------------------------|
| Nome ou comentário só com espaços                         | Recusado como vazio (CA-4, CA-6).                         |
| Nome com 121 caracteres                                   | Recusado (CA-4).                                          |
| Comentário com 1.001 caracteres                           | Recusado (CA-6).                                          |
| Nenhuma estrela escolhida                                 | Erro "Campo obrigatório." na nota (CA-5).                 |
| Nota 0, 6 ou fracionada enviada direto à API              | Recusada (CA-5, CA-7).                                    |
| A mesma pessoa avalia o mesmo filme duas vezes            | Aceito: são duas avaliações (D-10).                       |
| Lista expandida com "Mostrar mais" antes de salvar        | A lista volta a mostrar as 10 mais recentes, com a nova no topo (D-5). |
| Duplo clique em "Enviar avaliação"                        | Uma única avaliação gravada (CA-8).                       |
| Filme removido em outra aba                               | "Filme não encontrado." (CA-14).                          |
| Filme Planejado ou Em Produção                            | Aceita avaliação (CA-13).                                 |

## Requisitos não funcionais

- **RNF-1.** Salvar uma avaliação responde em até 1 s com o catálogo
  completo. *(A validar na implementação.)*

## Consequências conhecidas

- **Notas novas são sempre inteiras em estrelas.** As avaliações importadas
  têm notas fracionadas (ex.: 9,8 → 4,9 estrelas); as novas só valem 1, 2, 3,
  4 ou 5 estrelas (notas 2, 4, 6, 8 e 10 no banco).
- **`dim_reviews` não é atualizado.** O resumo importado já diverge das
  avaliações individuais (spec 000) e não é usado para exibir médias
  (constituição, seção 4.2); esta feature não o altera.
- **Datas.** As avaliações novas ficam com a data real de criação e aparecem
  antes das importadas, que têm todas a data da carga (spec 002).
- **Precisão de 1 segundo na data de criação.** O banco grava o
  `created_at` com precisão de segundos. Duas avaliações do mesmo filme
  criadas no mesmo segundo empatam na data e ficam na ordem da chave (estável,
  mas não necessariamente a mais nova primeira). Pela interface isso é
  praticamente impossível (exigiria enviar dois formulários no mesmo segundo),
  então a limitação foi aceita em vez de mudar a coluna com uma migração
  (decisão do desenvolvedor na fase 0 da implementação, 2026-09-26).

## Decisões

- **D-1.** O formulário fica fixo na seção de avaliações, acima da lista.
  *Descartado:* um botão que abre o formulário.
- **D-2.** O autor é um nome digitado, obrigatório: o administrador registra
  avaliações de pessoas diferentes, como nas importadas. *Descartado:* nome
  fixo "Administrador", com ou sem possibilidade de troca.
- **D-3.** Qualquer filme aceita avaliações, inclusive os não lançados,
  como na carga (579 avaliações nesses filmes). *Descartado:* restringir a
  filmes lançados.
- **D-4.** Comentário de até 1.000 caracteres. *Descartado:* 4.000 (o limite
  do banco) ou 500.

### Propostas desta spec (confirmar na revisão)

- **D-5.** Depois de salvar, a lista recarrega a partir das 10 mais recentes.
  A avaliação nova fica no topo, e "Mostrar mais" volta ao começo. É o
  jeito mais simples de a lista, o total e a paginação ficarem certos.
- **D-6.** A mensagem "Avaliação adicionada." usa o mesmo aviso de sucesso
  da feature 003 (topo da tela, some em 5 s).
- **D-7.** A nota começa sem estrela marcada, para que a escolha seja sempre
  consciente. Sem nota, aparece o erro de campo obrigatório.
- **D-8.** O contador de caracteres do comentário ajuda a respeitar o limite
  de 1.000.
- **D-9.** O limite do nome é 120 caracteres, o tamanho da coluna no banco.
  Os importados têm até 28.
- **D-10.** A mesma pessoa pode avaliar o mesmo filme mais de uma vez: não há
  identidade de usuário para garantir unicidade (spec 003: sem autenticação).

## Fora de escopo

- Editar ou remover avaliações.
- Meia estrela ou notas fracionadas na entrada.
- Contas de usuário, login ou identificar quem avaliou.
- Moderação, anti-spam ou limite de avaliações por pessoa.
- Atualizar o resumo `dim_reviews`.
- Ordenar ou filtrar a lista de avaliações de outras formas.
