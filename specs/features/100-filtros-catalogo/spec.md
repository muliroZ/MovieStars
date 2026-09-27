# 100 — Filtros e ordenação do catálogo

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Concluída                                              |
| Depende de     | 001 (catálogo e busca); usa componentes da 003 e da 004 |
| Bloqueia       | —                                                      |
| Referências    | `specs/constitution.md` (seções 1, 4.2, 4.6, 5.3); spec 001 |

## Contexto

O catálogo (feature 001) tem busca pelo título e sempre sai em ordem
alfabética. Com 95.645 filmes, o administrador não consegue ver, por
exemplo, "os dramas de 2020 mais bem avaliados" ou "os filmes que ainda não
têm avaliação".

A constituição reserva a numeração 100+ para features extras (seção 1) e
deixa as outras dimensões de busca para a spec que as introduzir (seção
4.6). Esta feature acrescenta ao catálogo **filtros** (gênero, ano, status,
avaliações e média mínima) e **ordenações** (título, ano, média e
quantidade de avaliações, nas duas direções), sem mudar o resto da tela.

Números dos dados atuais que afetam o comportamento:
- 20.037 filmes não têm gênero;
- 55.378 filmes não têm avaliação;
- os anos vão de 2016 a 2029;
- o máximo de avaliações por filme é 13.

## Histórias de usuário

- **H-1.** Como administrador, quero filtrar o catálogo por gênero, ano,
  status e avaliações, para encontrar um conjunto de filmes sem percorrer
  milhares de páginas.
- **H-2.** Como administrador, quero ordenar o catálogo por ano, média ou
  quantidade de avaliações, nas duas direções, para ver primeiro o que me
  interessa.
- **H-3.** Como administrador, quero recarregar ou compartilhar o endereço e
  voltar aos mesmos filtros e à mesma ordenação.

## Critérios de aceitação

### Barra e painel

- **CA-1** (H-1, H-2). Acima da grade do catálogo há uma barra com:
  - o botão **"Filtros"**, que mostra entre parênteses quantos filtros estão
    ativos (ex.: "Filtros (2)"), ou só "Filtros" se não houver nenhum;
  - o seletor de **ordenação**;
  - o botão **"Inverter"**, que mostra se está ligado.
- **CA-2** (H-1). O botão "Filtros" abre e fecha o painel de filtros. O
  painel começa fechado, e abrir ou fechar não muda a lista nem o endereço
  (D-12).

### Filtros

- **CA-3** (H-1). **Gêneros:** é possível marcar vários dos 19 gêneros,
  exibidos em ordem alfabética.
- **CA-4** (H-1). Uma chave define como os gêneros marcados se combinam:
  - **"Qualquer um"** (padrão): filmes com pelo menos um dos gêneros;
  - **"Todos"**: só filmes que têm todos os gêneros marcados.

  Com algum gênero marcado, filmes sem gênero nunca aparecem.
- **CA-5** (H-1). **Ano:** campos "de" e "até", inclusivos. Dá para
  preencher só um deles.
  - Os campos esperam **400 ms** sem digitação antes de aplicar (D-8).
  - Ano fora de 1888 até o ano atual + 10 mostra "Deve estar entre 1888 e
    <ano>." (a mesma regra da spec 003).
  - "De" maior que "até" mostra "O ano inicial deve ser menor ou igual ao
    final.".
  - Com erro, a lista não muda.
- **CA-6** (H-1). **Status:** é possível marcar vários dos 4 status
  (Lançado, Pós-Produção, Em Produção, Planejado). Nenhum marcado significa
  todos.
- **CA-7** (H-1). **Avaliações:** três opções exclusivas: **"Todos"**
  (padrão), **"Com avaliação"** e **"Sem avaliação"** (D-5).
- **CA-8** (H-1). **Mínimo de estrelas:** escolher de 1 a 5 estrelas mostra
  só filmes cuja **média exibida** (com 1 casa decimal) é maior ou igual à
  escolhida. Um filme exibido com "4,0" entra em "4 estrelas ou mais", mesmo
  que a média exata seja 3,96. Filmes sem avaliação não entram. O botão
  **"Qualquer nota"** limpa a escolha (D-4).
- **CA-9** (H-1). Escolher **"Sem avaliação"** limpa e desabilita o mínimo de
  estrelas, porque a combinação nunca teria resultados.
- **CA-10** (H-1). Os filtros se somam entre si e com a busca pelo título
  (spec 001). Um filtro vazio não restringe nada.
- **CA-11** (H-1). Cada mudança de filtro ou de ordenação vale na hora, sem
  botão "Aplicar", e volta para a página 1 (D-7).
- **CA-12** (H-1). O botão **"Limpar filtros"**, no painel, apaga todos os
  filtros e mantém a busca e a ordenação (D-13).

### Ordenação

- **CA-13** (H-2). O seletor de ordenação tem quatro campos, cada um com uma
  direção padrão:

  | Campo                     | Direção padrão          | Invertida                |
  |---------------------------|-------------------------|--------------------------|
  | Título (padrão do catálogo) | A–Z                   | Z–A                      |
  | Ano                       | mais recentes primeiro  | mais antigos primeiro    |
  | Média de estrelas         | maiores primeiro        | menores primeiro         |
  | Quantidade de avaliações  | mais avaliados primeiro | menos avaliados primeiro |

- **CA-14** (H-2). O botão "Inverter" troca a direção do campo escolhido
  (D-9). Trocar de campo mantém o "Inverter" como estava.
- **CA-15** (H-2). Filmes **sem valor** para o campo ficam **sempre no fim**,
  nas duas direções: sem ano, ao ordenar por ano; sem avaliação, ao ordenar
  pela média. Na ordenação por quantidade, filme sem avaliação conta como 0
  e segue a direção normalmente.
- **CA-16** (H-2). Empates são desempatados pelo título (A–Z), sem diferenciar
  acentos nem maiúsculas, e depois pelo ano. A ordem é sempre a mesma entre
  uma consulta e outra, então nenhum filme se repete ou some ao trocar de
  página.

### Resultado e endereço

- **CA-17** (H-1). O resumo acima da grade continua como na spec 001 ("N
  filmes", ou "N filmes encontrados para "termo"") e ganha " · K filtros
  ativos" quando K for maior que 0 (ex.: "1.234 filmes · 2 filtros ativos").
- **CA-18** (H-1). Um resultado vazio com filtros ativos mostra "Nenhum filme
  encontrado com os filtros escolhidos." e o botão "Limpar filtros". Sem
  filtros, vale a mensagem da spec 001.
- **CA-19** (H-3). Filtros e ordenação ficam no endereço, junto com a página
  e a busca. Os valores padrão não aparecem, então o catálogo sem filtros
  continua em `/`. Recarregar ou abrir o endereço em outra aba mostra os
  mesmos filtros e a mesma ordem. Os botões voltar e avançar do navegador
  percorrem as combinações visitadas.
- **CA-20** (H-3). Valores inválidos no endereço são ignorados, como a página
  inválida da spec 001 (CA-20):
  - um gênero que não existe sai do endereço;
  - valores como um mínimo de 9 estrelas, um ano "abc" ou uma ordenação
    desconhecida são desconsiderados.
- **CA-21** (H-1). As mesmas regras de validação valem na API, mesmo que a
  interface seja contornada, com as mensagens em português (spec 003,
  DEC-8).

### Estados e layout

- **CA-22**. Os estados de carregamento e erro são os mesmos do catálogo
  (spec 001, CA-21 e CA-22).
- **CA-23**. A tela é utilizável a partir de 360 px, sem rolagem horizontal:
  o painel fica em uma coluna em telas estreitas, e a barra de ordenação
  quebra linha quando precisa.

## Casos de borda

| Situação                                                     | Comportamento esperado                                   |
|--------------------------------------------------------------|----------------------------------------------------------|
| "Todos" com um gênero que nenhum filme combina               | Resultado vazio com a mensagem do CA-18.                 |
| Só o ano "até" preenchido                                    | Filmes até aquele ano (CA-5).                            |
| "De" 2025 e "até" 2020                                       | Erro no campo; a lista não muda (CA-5).                  |
| "Sem avaliação" com mínimo de estrelas escolhido antes       | O mínimo é limpo e desabilitado (CA-9).                  |
| Mínimo de 5 estrelas                                         | Só filmes com média exibida 5,0.                         |
| Ordenar pela média, invertido                                | Os pior avaliados primeiro; os sem avaliação no fim (CA-15). |
| Ordenar por quantidade                                       | Muitos empates (máximo de 13), resolvidos pelo título (CA-16). |
| Endereço com um gênero que não existe                        | O gênero sai do endereço e não filtra nada (CA-20).      |
| Busca sem resultados e nenhum filtro ativo                   | Mensagem da spec 001 (CA-18).                            |
| Filtros ativos e o painel fechado                            | O botão mostra "Filtros (N)" e o resumo mostra "K filtros ativos". |

## Requisitos não funcionais

- **RNF-1.** Com o catálogo completo, cada página do catálogo responde em
  até 1 s com qualquer combinação de filtros e ordenação, inclusive ao
  ordenar os 95.645 filmes pela média. *(A validar na implementação.)*

## Consequências conhecidas

- **Filmes sem gênero** (20.037) nunca aparecem quando algum gênero está
  marcado.
- **Ordenar por quantidade tem muitos empates:** quase todos os filmes têm
  0, 1 ou 2 avaliações.
- **Arredondamento:** em médias que caem exatamente na metade de uma casa
  decimal (ex.: 3,95), o filtro de mínimo de estrelas pode discordar da
  média exibida em 0,1. É raro, e o plan detalha o motivo.
- **Títulos com aspas extras** continuam no início da ordem por título A–Z,
  e no fim da Z–A (pendência adiada; spec 001, D-1).

## Decisões

- **D-1.** Filtros: gênero, ano, status, avaliações e mínimo de estrelas.
- **D-2.** Ordenações: título (padrão), ano, média de estrelas e quantidade
  de avaliações. *Descartado:* popularidade do TMDB.
- **D-3.** A chave "Qualquer um" (OU) / "Todos" (E) combina os gêneros, com
  "Qualquer um" como padrão. *Descartado:* um modo fixo.
- **D-4.** A média usa um mínimo de estrelas (1 a 5). *Descartado:* uma faixa
  de mínimo e máximo.
- **D-5.** O filtro de avaliações tem três opções: Todos, Com avaliação e Sem
  avaliação.
- **D-6.** Os filtros ficam num painel recolhível acima da grade, aberto pelo
  botão "Filtros (N)", com a ordenação sempre visível. *Descartado:* barra
  lateral; linha de menus suspensos.
- **D-7.** As mudanças valem na hora. *Descartado:* botão "Aplicar".
- **D-8.** Os campos de ano esperam 400 ms sem digitação (a busca pelo título
  continua com 300 ms).
- **D-9.** A ordenação tem campo e um botão "Inverter", e valores vazios
  ficam sempre no fim.
- **D-10.** A média continua calculada a partir das avaliações individuais a
  cada consulta (constituição, seção 4.2), agora também para filtrar e
  ordenar. *Descartado:* guardar a média pronta em cada filme, o que
  exigiria mudar a constituição.

### Propostas desta spec (confirmar na revisão)

- **D-11.** Textos:
  - chave de gêneros: "Qualquer um" / "Todos";
  - campos de ordenação: "Título", "Ano", "Média de estrelas" e "Quantidade
    de avaliações";
  - opções de avaliações: "Todos", "Com avaliação" e "Sem avaliação";
  - limpar o mínimo de estrelas: "Qualquer nota";
  - botões "Filtros (N)", "Inverter" e "Limpar filtros";
  - resumo "· K filtros ativos" e a mensagem do CA-18.
- **D-12.** O painel começa fechado, e se ele está aberto ou fechado não vai
  para o endereço (não é um filtro).
- **D-13.** "Limpar filtros" não apaga a busca nem a ordenação, que têm
  controles próprios ("Limpar" na busca, da spec 001).
- **D-14.** Um gênero inválido no endereço é retirado dele sem criar uma
  entrada no histórico do navegador.

## Fora de escopo

- Filtrar por diretor, elenco, produtora ou duração.
- Faixa de média (mínimo e máximo) e média com meia estrela no filtro.
- Ordenar por popularidade, notas externas (TMDB, IMDb), data de lançamento
  exata ou duração.
- Salvar combinações de filtros com nome ("filtros favoritos").
- Contagem de filmes por opção de filtro (ex.: "Drama (12.345)").
- Filtros na busca de diretores do formulário (spec 003).
- Corrigir títulos com aspas extras (pendência adiada).
