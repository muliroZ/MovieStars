# 003 — Gerenciar filmes

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Aprovada                                               |
| Depende de     | 001 (catálogo), 002 (página de detalhes)               |
| Bloqueia       | —                                                      |
| Referências    | `specs/constitution.md` (seções 1, 4.3, 4.4, 4.5, 5.2, 5.3) |

## Contexto

Até aqui o administrador só consulta o catálogo. Esta feature permite
cadastrar filmes novos, editar os existentes (inclusive os importados) e
removê-los.

A constituição já define três regras:
- gêneros são escolhidos entre os existentes, e diretores são buscados por
  nome e criados se não existirem (seção 4.3);
- o `id_filme` é gerado pelo sistema e nunca enviado pela interface (seção
  4.4);
- a remoção é definitiva, apaga em cascata as avaliações, os vínculos e as
  métricas, e sempre pede confirmação (seção 4.5).

Esta spec define o formulário, as validações, a escolha de diretores e o
comportamento da edição e da remoção.

## Histórias de usuário

- **H-1.** Como administrador, quero cadastrar um filme novo, para que ele
  apareça no catálogo e possa receber avaliações.
- **H-2.** Como administrador, quero corrigir os dados de um filme, para
  manter o catálogo correto.
- **H-3.** Como administrador, quero remover um filme, para tirar do
  catálogo o que não deve estar lá.
- **H-4.** Como administrador, quero ser avisado de erros no formulário antes
  de salvar, para não perder tempo nem gravar dados inválidos.

## Critérios de aceitação

### Cadastro

- **CA-1** (H-1). O cabeçalho do catálogo tem um botão "Novo filme", que abre
  o formulário de cadastro.
- **CA-2** (H-1). O formulário tem os campos abaixo. Os três primeiros são
  obrigatórios (D-2).

  | Campo                  | Tipo de entrada                                   |
  |------------------------|---------------------------------------------------|
  | Título *               | texto                                             |
  | Ano *                  | número                                            |
  | Status *               | escolha entre Lançado, Pós-Produção, Em Produção e Planejado |
  | Data de lançamento     | data                                              |
  | Duração (minutos)      | número                                            |
  | Sinopse                | texto longo                                       |
  | URL do pôster          | endereço                                          |
  | URL da imagem de fundo | endereço                                          |
  | Gêneros                | vários, entre os 19 existentes, em ordem alfabética |
  | Diretores              | vários, com sugestões (CA-16 a CA-19)             |

- **CA-3** (H-1). Ao salvar, o filme é criado com um `id_filme` gerado pelo
  sistema, que não aparece no formulário. O administrador é levado à página
  de detalhes do filme novo, com a mensagem "Filme cadastrado.".
- **CA-4** (H-1). O filme novo aparece na hora no catálogo e na busca, na
  posição alfabética correta (spec 001, CA-2 e CA-11).
- **CA-5** (H-1). Nos detalhes, o filme novo aparece sem avaliações, com os
  dados financeiros como "Não informado" e com Roteiro, Elenco e Produtoras
  como "Não informado" (spec 002).

### Validação

- **CA-6** (H-4). **Título:** obrigatório, com 1 a 500 caracteres depois de
  tirar os espaços do início e do fim. Um título só com espaços é recusado.
- **CA-7** (H-4). **Ano:** obrigatório, inteiro, de 1888 até o ano atual + 10
  (D-5).
- **CA-8** (H-4). **Data de lançamento:** opcional. Ao escolher uma data, o
  campo Ano é preenchido com o ano dela. Se os dois divergirem, aparece o
  erro "O ano deve ser o mesmo da data de lançamento." (D-6).
- **CA-9** (H-4). **Duração:** opcional, inteiro de 1 a 1.000 minutos. Campo
  vazio significa "não informada" (D-7).
- **CA-10** (H-4). **Status:** obrigatório, um dos quatro valores.
- **CA-11** (H-4). **Sinopse:** opcional, até 4.000 caracteres.
- **CA-12** (H-4). **URLs:** opcionais, até 2.048 caracteres, começando com
  `http://` ou `https://` (D-8).
- **CA-13** (H-4). **Gêneros:** opcionais, só entre os existentes. Não é
  possível criar gênero novo.
- **CA-14** (H-4). Cada erro aparece junto do campo, em português. O
  formulário não é enviado enquanto houver erro. As mesmas regras valem na
  API, mesmo que a interface seja contornada (constituição, seção 5.2).
- **CA-15** (H-4). Enquanto o formulário é salvo, o botão "Salvar" fica
  desabilitado, e um duplo clique não cria dois filmes. Se o salvamento
  falhar (API fora do ar, erro no servidor), aparece uma mensagem de erro, e
  o que foi digitado continua no formulário.

### Diretores

- **CA-16** (H-1, H-2). Ao digitar 2 ou mais letras no campo de diretor,
  aparecem até 10 sugestões de diretores já cadastrados cujo nome contém o
  texto, sem diferenciar maiúsculas nem acentos. Escolher uma sugestão
  adiciona aquele diretor (D-9).
- **CA-17** (H-1, H-2). Também é possível adicionar o nome digitado sem
  escolher uma sugestão. Se ele for **exatamente igual** ao nome de um
  diretor existente (ignorando só os espaços do início e do fim), esse
  diretor é reaproveitado. Caso contrário, um diretor novo é criado ao
  salvar, e o formulário marca o nome como "novo" antes disso (D-3).
- **CA-18** (H-1, H-2). Os diretores adicionados aparecem como etiquetas
  removíveis. O mesmo diretor não pode ser adicionado duas vezes ao mesmo
  filme.
- **CA-19** (H-4). Nome de diretor novo: 1 a 255 caracteres depois de tirar
  os espaços do início e do fim.

### Edição

- **CA-20** (H-2). A página de detalhes tem um botão "Editar", que abre o
  formulário já preenchido com os dados atuais do filme, inclusive gêneros e
  diretores.
- **CA-21** (H-2). Ao salvar, o filme é atualizado, e o administrador volta
  aos detalhes com a mensagem "Filme atualizado.". Um título alterado já
  vale para a busca e a ordem do catálogo.
- **CA-22** (H-2). A edição não altera roteiristas, elenco, produtoras,
  dados financeiros nem avaliações do filme.
- **CA-23** (H-2). Tirar um diretor do filme só desfaz o vínculo; a pessoa
  continua cadastrada e pode aparecer nas sugestões.
- **CA-24** (H-2). "Cancelar" volta aos detalhes sem salvar.
- **CA-25** (H-2). Abrir a edição de um filme inexistente mostra "Filme não
  encontrado". Se o filme for removido enquanto a edição está aberta,
  salvar mostra a mesma mensagem.

### Remoção

- **CA-26** (H-3). A página de detalhes tem um botão "Excluir". Ele abre uma
  confirmação com o título do filme e quantas avaliações serão apagadas
  junto (ex.: "As 13 avaliações deste filme também serão excluídas."), com
  os botões "Excluir definitivamente" e "Cancelar".
- **CA-27** (H-3). Ao confirmar, o filme é apagado definitivamente, junto com
  as avaliações, os vínculos com gêneros, pessoas e produtoras, as métricas
  e o resumo de avaliações (constituição, seção 4.5). O administrador vai
  para o catálogo com a mensagem "Filme excluído.".
- **CA-28** (H-3). Depois da remoção, o filme não aparece mais no catálogo
  nem na busca, e o endereço dele mostra "Filme não encontrado".
- **CA-29** (H-3). Pessoas, gêneros e produtoras que estavam ligados ao filme
  continuam cadastrados.
- **CA-30** (H-3). Se a remoção falhar, aparece uma mensagem de erro, e o
  filme continua existindo.

### Mensagens e layout

- **CA-31**. As mensagens de sucesso ("Filme cadastrado.", "Filme
  atualizado.", "Filme excluído.") aparecem no topo da página seguinte e
  somem sozinhas depois de alguns segundos, ou ao fechar.
- **CA-32**. O formulário de edição mostra um indicador enquanto carrega os
  dados do filme e uma mensagem de erro com "Tentar novamente" se a
  consulta falhar.
- **CA-33**. O formulário e a confirmação de remoção são utilizáveis a
  partir de 360 px de largura, sem rolagem horizontal.

## Casos de borda

| Situação                                                   | Comportamento esperado                                   |
|------------------------------------------------------------|----------------------------------------------------------|
| Título igual ao de outro filme                             | Aceito; 12.165 filmes já compartilham título (spec 001). |
| Título com espaços no início ou no fim                     | Os espaços são removidos ao salvar (D-10).               |
| Data 29/02 em ano não bissexto                             | Recusada como data inválida.                             |
| Data de 2017 com ano 2018                                  | Erro do CA-8.                                            |
| Duração 0 digitada                                         | Recusada (CA-9); para "não informada", deixa-se vazio.   |
| Editar filme importado com duração 0                       | O campo aparece vazio; ao salvar, a duração fica "não informada" (vazio) (D-7). |
| "Alberto Rodriguez" digitado, existindo só "Alberto Rodríguez" | Cria um diretor novo (CA-17); para usar o existente, escolhe-se a sugestão. |
| Mesmo diretor escolhido duas vezes                         | A segunda vez é ignorada (CA-18).                        |
| Todos os gêneros e diretores removidos na edição           | Aceito; os detalhes mostram "Sem gênero" e "Não informado". |
| Duplo clique em "Salvar" no cadastro                       | Um único filme é criado (CA-15).                         |
| Filme removido em outra aba e depois salvo                 | "Filme não encontrado" (CA-25).                          |
| Excluir filme sem avaliações                               | A confirmação não menciona avaliações.                   |
| Voltar do navegador depois de excluir                      | O endereço do filme mostra "Filme não encontrado".       |

## Requisitos não funcionais

- **RNF-1.** Salvar, excluir e buscar sugestões de diretor respondem em até
  1 s com o catálogo completo (65.200 diretores). *(A validar na
  implementação.)*

## Consequências conhecidas

- **Filmes novos sem métricas.** Não há campos financeiros no formulário
  (D-1), então filmes cadastrados pelo sistema não têm dados financeiros.
- **Diretores duplicados.** Um nome digitado com grafia diferente (acento,
  maiúsculas) cria um diretor novo, como já acontece em 23 casos da carga.
  As sugestões ignoram acentos, o que ajuda a escolher o existente.
- **Pessoas sem filme.** Remover filmes ou tirar diretores deixa pessoas sem
  nenhum filme ligado. Hoje já há 2.052 diretores assim; eles continuam
  disponíveis nas sugestões.
- **Editar pode normalizar dados importados.** Salvar um filme importado tira
  os espaços das pontas do título e troca a duração 0 por vazio, que é como
  a interface já os exibia.

## Decisões

- **D-1.** O formulário edita só os campos básicos, gêneros e diretores.
  Roteiro, elenco, produtoras e dados financeiros continuam vindo apenas da
  carga. *Descartado:* editar também roteiristas e elenco, produtoras ou
  dados financeiros.
- **D-2.** Título, ano e status são obrigatórios. *Descartado:* só o título;
  ou título, ano, gênero e diretor.
- **D-3.** Diretores: sugestões sem acentos e reaproveitamento só com o nome
  exato. *Descartado:* reaproveitar ignorando acentos, que seria ambíguo nos
  23 pares da carga.
- **D-4.** "Novo filme" fica no cabeçalho do catálogo; "Editar" e "Excluir"
  ficam na página de detalhes. *Descartado:* botões nos cartões.

### Propostas desta spec (confirmar na revisão)

- **D-5.** Ano de 1888 (o primeiro filme conhecido) até o ano atual + 10.
  Isso cobre os dados (2016 a 2029) e filmes planejados, e barra erros de
  digitação como 20017.
- **D-6.** A data preenche o ano automaticamente, e os dois precisam bater.
  Nos dados, o ano é sempre o da data.
- **D-7.** Duração de 1 a 1.000 minutos; vazio significa "não informada". O
  zero da carga (spec 000, D-2) não é aceito como entrada nova.
- **D-8.** URLs só com `http://` ou `https://`, para barrar textos que não
  são endereços. O formulário não baixa nem valida a imagem.
- **D-9.** Sugestões de diretor a partir de 2 letras, no máximo 10.
- **D-10.** Os espaços das pontas do título e dos nomes de diretor são
  removidos ao salvar. A D-3 da spec 000 mantinha esses espaços para os
  dados importados; aqui se trata de digitação nova.
- **D-11.** A confirmação de remoção informa quantas avaliações serão
  apagadas, porque a ação é definitiva.

## Fora de escopo

- Editar roteiristas, elenco, produtoras e dados financeiros (D-1).
- Criar, renomear ou remover gêneros e pessoas.
- Editar ou remover avaliações individuais; adicionar avaliação (feature
  004).
- Desfazer uma remoção, lixeira ou remoção lógica.
- Enviar arquivos de imagem; só URLs.
- Aviso de alterações não salvas ao sair do formulário.
- Detectar edições simultâneas do mesmo filme.
- Autenticação e permissões.
- Corrigir títulos com aspas extras (pendência adiada).
