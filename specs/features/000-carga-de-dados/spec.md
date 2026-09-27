# 000 — Carga de dados

| Campo          | Valor                                   |
|----------------|-----------------------------------------|
| Status         | Concluída                               |
| Depende de     | — (apenas das migrações do repositório base) |
| Bloqueia       | 001, 002, 003, 004                      |
| Referências    | `specs/constitution.md` (seções 4.1 e 4.2) |

## Contexto

O repositório base traz o esquema do banco, mas nenhuma rotina para
populá-lo. Os dados iniciais do catálogo são fornecidos em dez arquivos CSV,
versionados no repositório em `data/`:

- `data/bases_atv_dev1/`: `dim_movies.csv`, `dim_genres.csv`,
  `dim_people.csv`, `dim_companies.csv`, `dim_reviews.csv`;
- `data/bases_atv_dev_2/`: `bridge_movie_genre.csv`, `bridge_movie_person.csv`,
  `bridge_movie_company.csv`, `fact_movies_performance.csv`,
  `movies_reviews.csv` (avaliações individuais, gravadas na tabela
  `movie_reviews`).

Sem esses dados, nenhuma outra feature pode ser desenvolvida ou demonstrada
com conteúdo real. Esta feature garante que qualquer pessoa que clone o
repositório (incluindo quem for avaliar a atividade) consiga ter o banco
populado com um único comando.

## Histórias de usuário

- **H-1.** Como desenvolvedor, quero popular o banco a partir dos CSVs com
  um único comando, para trabalhar nas features com dados reais.
- **H-2.** Como avaliador da atividade, quero seguir o README e ter a
  aplicação funcionando com o catálogo completo, sem passos manuais.
- **H-3.** Como desenvolvedor, quero poder rodar a carga de novo sem
  corromper nem duplicar dados, para não ter medo de executá-la duas vezes.
- **H-4.** Como desenvolvedor, quero saber exatamente o que foi carregado e
  o que foi descartado, para confiar nos dados que aparecem na aplicação.

## Critérios de aceitação

### Execução

- **CA-1** (H-1, H-2). Um único comando carrega todos os CSVs no banco.
- **CA-2** (H-1). O local dos CSVs pode ser informado na execução; se omitido,
  é usada a pasta `data/` do repositório, com a estrutura de subpastas
  descrita no Contexto. A pasta padrão é documentada no README.
- **CA-3** (H-2). A carga não cria nem altera tabelas. Se as migrações ainda
  não tiverem sido aplicadas, a execução é interrompida com uma mensagem
  orientando a rodar as migrações primeiro.
- **CA-4** (H-2). O `README.md` principal do projeto descreve o comando de
  carga no passo a passo de execução, na posição correta (depois das
  migrações, antes de subir a API). O `README-BASE.md`, herdado do
  repositório da atividade, não é alterado.

### Resultado

- **CA-5** (H-1). Em um banco recém-migrado e vazio, todas as linhas válidas
  de todos os CSVs são gravadas nas tabelas correspondentes.
- **CA-6** (H-1). Após a carga, não existe nenhum registro órfão: toda
  associação, métrica e avaliação aponta para um filme (e, quando for o
  caso, gênero, pessoa ou produtora) existente.
- **CA-7** (H-1). Células vazias nos CSVs são gravadas como ausência de valor
  (nulo), e não como texto vazio ou zero.
- **CA-8** (H-1). Textos com acentos e caracteres especiais (títulos,
  sinopses, nomes, comentários) são preservados sem alteração, inclusive
  espaços no início ou no fim (D-3). A única exceção é a correção de aspas
  das sinopses (CA-18).
- **CA-9** (H-1). As notas de `movie_reviews` são gravadas como estão no CSV
  (escala 0–10), sem conversão. A conversão para estrelas é responsabilidade
  da API (constituição, seção 4.1).

### Reexecução

- **CA-10** (H-3). Executar a carga sobre um banco já populado não duplica
  registros nem termina em erro. Registros já existentes (mesma chave) são
  mantidos como estão e contabilizados como "ignorados".
- **CA-11** (H-3). Existe uma opção explícita para apagar os dados e
  recarregar tudo do zero. Essa opção nunca é o comportamento padrão.

### Validação e falhas

Inconsistências de conteúdo que o banco aceita (ex.: duração 0, resumo de
avaliações divergente, espaços nas bordas) são gravadas como estão (D-4).
Os critérios abaixo tratam apenas de valores que o banco não aceita.

- **CA-12** (H-4). Linhas com problemas em campos obrigatórios (ex.: título
  vazio, nota fora de 0–10, tipo de pessoa diferente de Ator, Diretor ou
  Roteirista, referência a filme inexistente) são descartadas sem
  interromper a carga das demais.
- **CA-13** (H-4). Campos opcionais com valor inválido (ex.: data em formato
  irreconhecível) são gravados como nulo, e a linha é mantida.
- **CA-14** (H-4). Se um arquivo esperado não existir ou não tiver as colunas
  necessárias, a carga é interrompida **antes de gravar qualquer dado**, com
  mensagem indicando o arquivo e as colunas ausentes.
- **CA-15** (H-3). Se a carga falhar no meio por qualquer outro motivo, o
  banco volta ao estado anterior à execução; nunca fica parcialmente
  carregado.

### Relatório

- **CA-16** (H-4). Ao final, é exibido um resumo por tabela com: linhas
  lidas, inseridas, ignoradas (já existentes) e descartadas (inválidas).
- **CA-17** (H-4). Para cada linha descartada ou campo anulado, o relatório
  informa arquivo, número da linha e motivo. Quando houver muitas
  ocorrências do mesmo motivo, é aceitável agrupá-las (ex.: "142 linhas
  descartadas em movies_reviews.csv: filme inexistente").

### Correção de dados

- **CA-18** (H-1, H-4). Sinopses que começam com aspas trazem um defeito de
  escape da origem: aspas envolvendo o texto e aspas internas dobradas
  (ex.: `"Julia ... a ""movie within the movie"" ..."`). Para essas
  sinopses, a carga:
  1. remove a aspa inicial;
  2. remove a aspa final somente se o texto terminar com um número ímpar de
     aspas seguidas. Uma aspa é a de fechamento. Três são uma aspa interna
     dobrada seguida da de fechamento. Duas são só uma aspa interna dobrada,
     porque o texto foi cortado logo depois dela e não tem fechamento;
  3. troca cada par de aspas internas (`""`) por uma só (`"`).

  Sinopses que não começam com aspas não são alteradas. O relatório informa
  quantas sinopses foram corrigidas (D-1).
- **CA-19** (H-1, H-4). Títulos que começam com aspas trazem o mesmo defeito
  (ex.: `"floyd ""money"" Mayweather"`). A carga aplica a eles os passos do
  CA-18 e, depois, põe em maiúscula a primeira letra do título, que a origem
  deixou minúscula porque contou a aspa como o primeiro caractere
  (`Floyd "money" Mayweather`). Títulos que não começam com aspas não são
  alterados. O relatório informa quantos títulos foram corrigidos (D-5).
  *(Alteração de 2026-09-27.)*

## Casos de borda

| Situação                                                        | Comportamento esperado                                     |
|-----------------------------------------------------------------|------------------------------------------------------------|
| Mesma chave aparece duas vezes no mesmo CSV                     | A primeira ocorrência é gravada; as demais são descartadas (CA-12). |
| Dois gêneros com o mesmo nome e chaves diferentes               | O primeiro é gravado; o segundo é descartado, e associações que apontem para ele também (CA-6, CA-12). |
| Mesma pessoa com mesmo nome e tipo, chaves diferentes           | Mesmo tratamento dos gêneros duplicados.                   |
| Mesmo nome de pessoa com tipos diferentes (ex.: Ator e Diretor) | São pessoas distintas; ambas são gravadas.                 |
| Dois filmes com o mesmo `id_filme`                              | O primeiro é gravado; o segundo é descartado (CA-12).      |
| Avaliação sem comentário                                        | Descartada: o comentário é obrigatório no banco (CA-12).   |
| CSV vazio (só cabeçalho)                                        | Não é erro; a tabela fica com zero registros inseridos (CA-16). |
| Linha com colunas a mais ou a menos que o cabeçalho             | Descartada, com o motivo no relatório (CA-12, CA-17).      |
| Coluna extra no cabeçalho que não existe na tabela              | Ignorada silenciosamente; não impede a carga.              |
| Sinopse começando com aspas (com ou sem aspa final)             | Corrigida conforme CA-18.                                  |
| `duracao_minutos` igual a 0                                     | Gravado como está (D-2).                                   |
| Contagens escritas com casa decimal (ex.: `2375.0`)             | Gravadas como número inteiro (`2375`); não é transformação de dado. |

## Requisitos não funcionais

- **RNF-1.** A carga completa termina em menos de 1 minuto em uma máquina de
  desenvolvimento comum. O volume é de cerca de 1,71 milhão de linhas
  (233 MB); só a leitura de todos os arquivos leva cerca de 3 s, então a
  meta é viável se a gravação for feita em lotes. A validar na implementação.
- **RNF-2.** A carga não depende de acesso à internet.

## Consequências conhecidas

- **Data das avaliações importadas.** O CSV de `movie_reviews` não tem data;
  o banco preenche `created_at` no momento da carga. Portanto, todas as
  avaliações importadas terão praticamente a mesma data, e ordenar por data
  só é significativo para avaliações criadas depois pelo sistema. As features
  002 e 004 devem levar isso em conta.
- **`dim_reviews` diverge de `movie_reviews`.** O resumo de avaliações é
  carregado como está, mas não é usado para exibir médias (constituição,
  seção 4.2). Nos dados atuais, a quantidade de avaliações bate em 22.101 de
  26.604 filmes, a média bate em 20.003 de 25.423, e 14.561 filmes com
  avaliações não aparecem em `dim_reviews`.
- **Sinopses cortadas na origem.** 3.312 das sinopses corrigidas pelo CA-18
  vêm cortadas no meio do texto (só 6 terminam com pontuação final). O
  texto perdido não pode ser recuperado; a carga grava o que existe.
- **Duração 0.** 10.160 filmes (10,6%) têm `duracao_minutos = 0`, que
  provavelmente significa "desconhecida". O valor é gravado como está, e as
  features que exibem a duração (001, 002, 003) devem mostrá-lo como "não
  informada" (D-2).
- **Filmes futuros.** Há datas de lançamento até 2029 (filmes com status
  Planejado, Em Produção ou Pós-Produção). São dados válidos.

## Premissas (confirmadas contra os arquivos reais)

- **P-1. Confirmada, com uma exceção de nome.** Cada CSV corresponde a
  exatamente uma tabela, e o cabeçalho tem os mesmos nomes das colunas do
  banco. Única exceção: o arquivo `movies_reviews.csv` alimenta a tabela
  `movie_reviews`. Todos os valores cabem nos tamanhos e tipos das colunas.
- **P-2. Confirmada.** Os CSVs já trazem as chaves substitutas (`sk_*`, 64
  caracteres hexadecimais) prontas, e as tabelas de associação referenciam
  essas mesmas chaves. Nos dados atuais não há chaves duplicadas, nomes
  duplicados nem registros órfãos.
- **P-3. Confirmada.** Todos os arquivos estão em UTF-8, sem BOM.

## Decisões tomadas na revisão

- **D-1.** Sinopses com defeito de escape de aspas são corrigidas (CA-18),
  em vez de gravadas como estão. Motivo: as aspas extras são um defeito da
  origem, não conteúdo, e apareceriam na tela do filme. Afeta 4.801
  sinopses: 1.489 completas, com aspa de fechamento, e 3.312 cortadas, sem
  fechamento. Destas, 2.825 não terminam em aspas e 487 terminam em uma
  aspa interna dobrada. A regra da aspa final por número ímpar foi ajustada
  durante a implementação (T-06, 2026-09-26), aprovada pelo desenvolvedor.
- **D-2.** `duracao_minutos = 0` é gravado como está; a interface trata o
  valor como "não informada". Alternativa descartada: gravar como nulo, que
  seria uma transformação de dado.
- **D-3.** Espaços no início ou no fim de textos são mantidos (3 títulos, 24
  sinopses, 4 nomes de pessoas, 4 produtoras). Alternativa descartada:
  removê-los. São poucos casos e não afetam o uso.
- **D-4.** Regra geral: inconsistências de conteúdo nos CSVs são gravadas no
  banco como estão. As únicas correções aplicadas são as das aspas nas
  sinopses e nos títulos (D-1, CA-18; D-5, CA-19). Linhas ou campos só são descartados ou anulados quando o
  banco não aceitaria o valor (CA-12, CA-13). Alternativa descartada:
  corrigir caso a caso. Isso aumentaria o escopo da carga e afastaria o
  banco dos dados de origem.
- **D-5.** Os 55 títulos com defeito de aspas são corrigidos (CA-19), com a
  primeira letra em maiúscula. Motivo: eles abriam a ordem alfabética do
  catálogo e apareciam com aspas extras e inicial minúscula. A regra é a
  mesma do CA-18, sem casos especiais:
  - 51 títulos ficam sem aspas nas pontas;
  - `"Blessed"` e `"Truelove: The Film"` continuam entre aspas, que fazem
    parte do título na origem;
  - `Headwind"21` e `Wwe Rivals: Bret "the Hitman" Hart Vs. Shawn Michaels"`
    ficam com uma aspa sem par, como na origem.

  O título `8' 19""` não começa com aspas e fica como está. Nomes de pessoas
  e produtoras com trechos de sinopse são outro defeito e continuam como
  estão. Nos bancos já carregados, a correção vem pela migração 0005.
  Decisão de 2026-09-27, aprovada pelo desenvolvedor.
  *Descartado:* manter a inicial minúscula, o que deixaria 52 títulos
  diferentes do resto do catálogo.

## Fora de escopo

- Interface web para enviar CSVs.
- Atualizar (sobrescrever) registros já existentes com dados novos do CSV.
- Carga incremental, agendada ou a partir de fontes externas (APIs, TMDB).
- Transformar ou enriquecer os dados (conversão de moeda, recálculo de
  lucro, recálculo de `dim_reviews`), exceto as correções de aspas do CA-18
  e do CA-19.
- Recuperar o texto das sinopses cortadas na origem.
- Geração de dados fictícios adicionais.
- O "contexto generativo" citado no README do repositório base.

## Questões resolvidas

- **Q-1. Nomes dos arquivos:** ver a lista no Contexto. São dez arquivos em
  duas subpastas de `data/`.
- **Q-2. Formato:** separador vírgula, com aspas no padrão CSV. Datas no
  formato `AAAA-MM-DD`. Decimais com ponto. Contagens escritas com casa
  decimal (`2375.0`), mas todas são inteiras. `movies_reviews.csv` usa
  quebra de linha CRLF; os demais usam LF.
- **Q-3. Volume por arquivo (linhas de dados, sem o cabeçalho):**

  | Arquivo                       | Linhas  |
  |-------------------------------|--------:|
  | `dim_movies.csv`              |  95.645 |
  | `dim_genres.csv`              |      19 |
  | `dim_people.csv`              | 424.656 |
  | `dim_companies.csv`           |  45.941 |
  | `dim_reviews.csv`             |  26.604 |
  | `bridge_movie_genre.csv`      | 121.521 |
  | `bridge_movie_person.csv`     | 745.450 |
  | `bridge_movie_company.csv`    | 116.326 |
  | `fact_movies_performance.csv` |  95.645 |
  | `movies_reviews.csv`          |  43.666 |

- **Q-4. Versionamento:** os CSVs já estão versionados em `data/` (commit
  `8dd3e15`); o avaliador os recebe ao clonar o repositório, e o
  `README.md` principal só precisa indicar a pasta padrão (CA-2, CA-4). Atenção:
  `bridge_movie_person.csv` tem 97 MB, perto do limite de 100 MB por
  arquivo do GitHub.

> Q-1 a Q-4 estão respondidas e P-1 a P-3 confirmadas. Spec **aprovada**
> pelo desenvolvedor em 2026-09-26.
