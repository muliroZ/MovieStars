# 002 — Detalhes do filme e média

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Aprovada                                               |
| Depende de     | 001 (o cartão do catálogo leva a esta página)          |
| Bloqueia       | 003 (editar/remover a partir dos detalhes), 004 (adicionar avaliação) |
| Referências    | `specs/constitution.md` (seções 1, 4.1, 4.2, 4.3, 4.4, 5.3) |

## Contexto

Na feature 001, clicar num cartão do catálogo leva a `/filmes/<chave>`, que
por enquanto mostra "Página não encontrada". Esta feature entrega a página
de detalhes: todas as informações do filme, a média geral das avaliações e a
lista das avaliações individuais.

A constituição já define como a média é calculada e exibida (seções 4.1 e
4.2). Esta spec define o que a página mostra, como as avaliações são
listadas e como a página reage a filmes inexistentes, dados ausentes e
falhas.

## Histórias de usuário

- **H-1.** Como administrador, quero ver todas as informações de um filme
  numa página, para conhecê-lo sem consultar o banco.
- **H-2.** Como administrador, quero ver a média geral e as avaliações
  individuais, para entender o que os usuários acham do filme.
- **H-3.** Como administrador, quero voltar ao catálogo no ponto em que
  estava, para continuar a navegação.

## Critérios de aceitação

### Acesso à página

- **CA-1** (H-1). Clicar num cartão do catálogo abre a página de detalhes
  daquele filme, no endereço `/filmes/<chave do filme>`.
- **CA-2** (H-1). O endereço pode ser recarregado ou aberto diretamente e
  mostra o mesmo filme.
- **CA-3** (H-1). Uma chave que não corresponde a nenhum filme mostra "Filme
  não encontrado" e um link para o catálogo.

### Informações do filme

- **CA-4** (H-1). A página mostra:
  - o pôster, ou a imagem padrão quando não houver ou não carregar (como no
    catálogo);
  - o título, exatamente como está no banco;
  - o ano e a data de lançamento no formato dd/mm/aaaa;
  - a duração no formato "1 h 42 min" (ou "58 min" abaixo de uma hora);
  - o status (Lançado, Planejado, Em Produção, Pós-Produção);
  - a sinopse completa;
  - todos os gêneros, em ordem alfabética.
- **CA-5** (H-1). Informações ausentes aparecem com texto explícito, e não
  como campo vazio:
  - "Data não informada";
  - "Duração não informada", também quando a duração for 0 (spec 000,
    D-2);
  - "Status não informado";
  - "Sinopse não informada";
  - "Sem gênero".
- **CA-6** (H-1). Quando o filme tem imagem de fundo (`url_backdrop`), ela
  aparece como faixa no topo da página. Sem imagem de fundo, ou se ela não
  carregar, a faixa não aparece e o layout não quebra.

### Equipe, elenco e produtoras

- **CA-7** (H-1). Há três listas de pessoas: Direção, Roteiro e Elenco,
  cada uma em ordem alfabética.
- **CA-8** (H-1). Há uma lista de produtoras, em ordem alfabética.
- **CA-9** (H-1). Cada lista mostra até 10 nomes. Se houver mais, aparece um
  botão "Mostrar todos (N)" que exibe a lista completa, e depois "Mostrar
  menos".
- **CA-10** (H-1). Uma lista vazia mostra "Não informado".

### Dados financeiros

- **CA-11** (H-1). A página mostra orçamento, receita e lucro, cada um em
  real e em dólar, como estão no banco, sem conversão. Formatos: "R$
  78.682.500,00" e "US$ 25.000.000,00".
- **CA-12** (H-1). Orçamento ou receita ausente aparece como "Não
  informado".
- **CA-13** (H-1). O lucro só é exibido quando orçamento **e** receita
  existem. Caso contrário, aparece "Não calculado" (D-5).
- **CA-14** (H-1). Lucro negativo aparece com sinal de menos e destacado
  como prejuízo (ex.: "−R$ 7.500.000,00").

### Média geral

- **CA-15** (H-2). A página mostra a média geral em estrelas, com uma casa
  decimal e meia estrela quando houver, e a quantidade de avaliações. Ela é
  calculada como no catálogo (constituição, seção 4.2; spec 001, CA-7).
  Sem avaliações, aparece "Sem avaliações".
- **CA-16** (H-2). A média e a quantidade da página de detalhes são
  **iguais** às do cartão do mesmo filme no catálogo.

### Avaliações

- **CA-17** (H-2). As avaliações aparecem das mais recentes para as mais
  antigas. Avaliações com a mesma data aparecem sempre na mesma ordem.
- **CA-18** (H-2). Cada avaliação mostra o nome de quem avaliou, a nota em
  estrelas com uma casa decimal (nota do banco ÷ 2, ex.: 9,8 → 4,9
  estrelas), o comentário e a data no formato dd/mm/aaaa.
- **CA-19** (H-2). São exibidas 10 avaliações de início. Se houver mais,
  aparece o botão "Mostrar mais avaliações", que acrescenta as próximas 10
  abaixo das já exibidas. O botão some quando todas estiverem na tela.
- **CA-20** (H-2). O título da seção mostra o total (ex.: "Avaliações
  (12)").
- **CA-21** (H-2). Um filme sem avaliações mostra "Este filme ainda não tem
  avaliações."
- **CA-22** (H-2). Se "Mostrar mais avaliações" falhar, as avaliações já
  exibidas continuam na tela, e aparece uma mensagem de erro com a opção de
  tentar de novo.

### Navegação

- **CA-23** (H-3). Há um link "Voltar ao catálogo". Se o administrador veio
  do catálogo, ele volta à mesma página e à mesma busca de onde saiu; se
  abriu o endereço direto, vai para o início do catálogo.
- **CA-24** (H-3). O botão voltar do navegador também leva de volta ao
  catálogo no mesmo ponto.
- **CA-25** (H-1). A aba do navegador mostra o título do filme (ex.:
  "Rings — MovieStars").

### Estados e layout

- **CA-26**. Enquanto os dados carregam, a página mostra um indicador de
  carregamento.
- **CA-27**. Se a consulta falhar (ex.: API fora do ar), a página mostra uma
  mensagem de erro em português e um botão "Tentar novamente".
- **CA-28**. A página é utilizável a partir de 360 px de largura, sem
  rolagem horizontal. Em telas estreitas, pôster e informações ficam um
  abaixo do outro.

## Casos de borda

| Situação                                                   | Comportamento esperado                                   |
|------------------------------------------------------------|----------------------------------------------------------|
| Chave inexistente ou com formato estranho na URL           | "Filme não encontrado" + link para o catálogo (CA-3).    |
| Duração 0                                                  | "Duração não informada" (CA-5).                          |
| Duração acima de 300 min (107 filmes)                      | Exibida como está (ex.: "13 h 19 min"; spec 000, D-4).   |
| Filme com 88 diretores                                     | 10 nomes e "Mostrar todos (88)" (CA-9).                  |
| Só orçamento conhecido (6.296 filmes)                      | Receita "Não informado"; lucro "Não calculado" (CA-13).  |
| Nem orçamento nem receita (85.976 filmes)                  | Os três aparecem como "Não informado"/"Não calculado".   |
| Filme sem imagem de fundo (38.308)                         | Sem faixa no topo (CA-6).                                |
| Exatamente 10 avaliações                                   | Todas exibidas, sem botão "Mostrar mais" (CA-19).        |
| 13 avaliações                                              | 10 exibidas; "Mostrar mais" traz as outras 3 e some.     |
| Nota 0 em uma avaliação                                    | "0,0" com as 5 estrelas vazias.                          |
| Título com aspas extras (spec 001, D-1)                    | Exibido como está.                                       |

## Requisitos não funcionais

- **RNF-1.** Com o catálogo completo, a página de detalhes e cada "Mostrar
  mais avaliações" respondem em até 1 s numa máquina de desenvolvimento
  comum. *(A validar na implementação.)*

## Consequências conhecidas

- **Datas das avaliações importadas.** As 43.666 avaliações vindas do CSV
  mostram todas a data da carga (ex.: 26/09/2026), porque o CSV não tem data
  (spec 000). Entre elas, a ordem é estável, mas não reflete quando foram
  escritas. Avaliações criadas pelo sistema (feature 004) aparecem antes,
  com a data real.
- **Elenco em ordem alfabética.** Os dados não informam a ordem de
  importância dos atores (protagonista, coadjuvante), então o elenco
  aparece em ordem alfabética.
- **Dados financeiros escassos.** Só 1.630 filmes têm orçamento e receita;
  na maioria das páginas, a seção financeira mostra "Não informado".
- **Nomes com aspas.** Alguns nomes de pessoas (175) e produtoras (33) são
  pedaços de sinopse que caíram na coluna errada na origem. Eles são
  exibidos como estão (pendência adiada, como os títulos com aspas).
- **Nova avaliação durante a navegação.** Se uma avaliação for criada
  enquanto a lista está parcialmente carregada, o "Mostrar mais" pode
  repetir uma avaliação já exibida. Com um único administrador, isso é
  improvável e não é tratado.

## Decisões

- **D-1.** A página tem as seções Equipe e elenco, Produtoras e Dados
  financeiros, além das informações básicas. *Descartado:* notas externas
  (TMDB, IMDb) e popularidade.
- **D-2.** Os valores financeiros aparecem em real e em dólar, lado a lado,
  como vêm nos dados. *Descartado:* mostrar só uma das moedas.
- **D-3.** As avaliações aparecem das mais recentes para as mais antigas,
  **com** a data. *Descartado:* esconder a data, ou ordenar por nota.
- **D-4.** As avaliações são carregadas 10 por vez, com "Mostrar mais".
  *Descartado:* carregar todas de uma vez.

### Propostas desta spec (confirmar na revisão)

- **D-5.** O lucro só aparece quando orçamento e receita existem. Nos dados,
  o lucro vale "−orçamento" quando falta a receita e 0 quando faltam os
  dois. Exibir esses valores sugeriria prejuízos e empates que não
  aconteceram. O banco continua como está (spec 000, D-4); é só uma regra de
  exibição.
- **D-6.** Até 10 nomes por lista de pessoas ou produtoras, com "Mostrar
  todos (N)". Isso cobre 99,5% dos filmes sem botão e evita páginas enormes
  nos casos extremos (88 diretores, 52 roteiristas).
- **D-7.** A imagem de fundo aparece como faixa no topo quando existe
  (CA-6). *Alternativa:* não usar a imagem de fundo.
- **D-8.** "Voltar ao catálogo" leva ao ponto exato de onde o
  administrador saiu, com a mesma página e busca (CA-23), e não sempre ao
  início do catálogo.
- **D-9.** O título do filme aparece na aba do navegador (CA-25).

## Fora de escopo

- Editar ou remover o filme (feature 003).
- Adicionar avaliação (feature 004).
- Editar ou remover avaliações.
- Notas externas (TMDB, IMDb), popularidade e o resumo de `dim_reviews`
  (D-1; constituição, seção 4.2).
- Páginas próprias de pessoas ou produtoras (links a partir dos nomes).
- Idade/classificação indicativa, trailer e filmes relacionados.
- Corrigir títulos, nomes ou valores (spec 000, D-4).
