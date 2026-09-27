# 101 — Cache de consultas

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Aprovada                                               |
| Depende de     | 100 (filtros e ordenação); 003 e 004 (as alterações que invalidam o cache) |
| Bloqueia       | —                                                      |
| Referências    | `specs/constitution.md` (seções 1, 4.2, 6); spec 100 (D-10); plan 100 (Riscos) |

## Contexto

O plan 100 mediu o catálogo com o `moviestars.db`: ordenar pela média ou
pela quantidade de avaliações leva de 186 a 456 ms. O motivo é que a média é
calculada a partir das avaliações individuais a cada consulta (constituição,
seção 4.2; spec 100, D-10). A última página ordenada pela média, por exemplo,
leva de 376 a 448 ms.

O catálogo repete muito as mesmas consultas: ao voltar da página de detalhes,
ao ir e voltar entre páginas, ao desfazer um filtro. E os dados só mudam
quando o administrador faz uma alteração: cadastrar, atualizar ou remover um
filme, ou adicionar uma avaliação.

Esta feature guarda por um tempo o resultado das consultas do catálogo e da
lista de gêneros, para que uma consulta repetida responda sem refazer o
cálculo. Toda alteração descarta o que foi guardado, para que o administrador
nunca veja um dado desatualizado depois de uma alteração feita pela
aplicação.

## Histórias de usuário

- **H-1.** Como administrador, quero que uma página do catálogo que eu já
  abri responda na hora quando eu voltar a ela, mesmo com uma ordenação cara.
- **H-2.** Como administrador, quero ver o resultado de uma alteração
  (filme novo, editado ou removido, avaliação nova) na próxima vez que abrir
  o catálogo, sem esperar o cache expirar.
- **H-3.** Como desenvolvedor, quero ligar e desligar o cache e saber, em
  cada resposta, se ela veio do cache, para conferir e depurar o
  comportamento.

## Critérios de aceitação

Neste documento, **acerto** é uma resposta que veio do cache, **falha** é uma
resposta calculada no banco com o cache ligado, e **desligado** é uma
resposta com o cache desligado.

### Consultas guardadas

- **CA-1** (H-1, H-3). A mesma consulta do catálogo feita duas vezes seguidas:
  a primeira é uma falha e a segunda um acerto, com conteúdo idêntico ao da
  primeira (D-2, D-6).
- **CA-2** (H-1). Consultas com os mesmos gêneros ou status em outra ordem
  (ex.: Drama e Horror, ou Horror e Drama) são a mesma consulta: a segunda é
  um acerto (D-3).
- **CA-3** (H-1). Consultas que diferem em qualquer outro ponto (página,
  tamanho da página, busca, filtros, ordenação ou "Inverter") são guardadas
  separadamente (D-3).
- **CA-4** (H-1, H-3). A lista de gêneros segue a mesma regra: falha na
  primeira vez e acerto na seguinte, com o mesmo conteúdo (D-2).
- **CA-5** (H-3). Uma consulta recusada por dados inválidos não é guardada e
  não informa acerto nem falha; a mesma consulta, corrigida, começa com uma
  falha (D-3).
- **CA-6**. Detalhes do filme, avaliações e busca de diretores não passam pelo
  cache e não informam acerto nem falha (D-2).
- **CA-7** (H-3). Cada resposta do catálogo e da lista de gêneros informa se
  foi um acerto, uma falha ou se o cache está desligado (D-6).

### Invalidação

- **CA-8** (H-2). Depois de uma avaliação adicionada com sucesso, a próxima
  consulta do catálogo é uma falha e já mostra a nova média e a nova
  quantidade de avaliações do filme, inclusive quando a consulta está
  ordenada ou filtrada pela média (D-4).
- **CA-9** (H-2). O mesmo vale depois de cadastrar, atualizar e remover um
  filme: a próxima consulta do catálogo é uma falha e mostra o filme novo, os
  dados alterados ou a ausência do filme removido, com o total e a paginação
  corretos (D-4).
- **CA-10** (H-2). Toda alteração bem-sucedida descarta **tudo** o que está
  guardado, inclusive a lista de gêneros e as consultas sem relação aparente
  com o filme alterado (D-4).
- **CA-11** (H-2). Uma alteração que falha (filme inexistente ou dados
  inválidos) não descarta nada (D-4).
- **CA-12** (H-2). Uma consulta que começou antes de uma alteração e termina
  depois dela não guarda o seu resultado: a próxima consulta igual é uma
  falha e mostra os dados já com a alteração (D-5).

### Expiração e limite

- **CA-13**. Passados 300 s desde que foi guardado, um resultado expira: a
  próxima consulta igual é uma falha (D-7).
- **CA-14**. Com o limite de 256 resultados guardados atingido, guardar um
  novo descarta o **menos usado recentemente**. Um resultado lido num acerto
  passa a contar como usado agora (D-7).

### Configuração

- **CA-15** (H-3). Com o cache desligado, nada é guardado: todas as respostas
  do catálogo e da lista de gêneros são calculadas no banco e informam que o
  cache está desligado (D-8).
- **CA-16** (H-3). O tempo de expiração e o limite de resultados são
  ajustáveis pela configuração, com os padrões 300 s e 256, documentados no
  README (D-8).
- **CA-17**. Com o cache ligado ou desligado, as respostas do catálogo e da
  lista de gêneros têm o mesmo conteúdo; só a indicação de acerto, falha ou
  desligado muda.

## Casos de borda

| Situação                                                        | Comportamento esperado                                   |
|-----------------------------------------------------------------|----------------------------------------------------------|
| Página além da última (lista vazia)                             | É uma resposta válida e é guardada como as outras.       |
| Avaliação nova num filme que não aparece na página guardada     | A página é descartada mesmo assim (CA-10).               |
| Dados alterados pela carga dos CSVs ou direto no banco          | Nada é descartado; o dado novo aparece quando o resultado expira (D-7). |
| Migração de dados aplicada com a aplicação no ar                | Mesmo caso da linha anterior; reiniciar a aplicação também esvazia o cache. |
| Duas consultas iguais ao mesmo tempo, sem resultado guardado    | As duas são falhas; a segunda a terminar guarda o mesmo resultado por cima. |
| Reiniciar a aplicação                                           | O cache começa vazio.                                    |
| Tempo de expiração ou limite inválidos na configuração          | A aplicação não inicia e aponta a configuração inválida, como as demais. |

## Requisitos não funcionais

- **RNF-1.** Um acerto da última página ordenada pela média responde em menos
  de 10 ms (hoje a falha leva de 376 a 448 ms). *(A medir no plan, como no
  plan 100.)*
- **RNF-2.** Uma falha não fica mais lenta que hoje de forma perceptível: os
  tempos do plan 100 continuam valendo.

## Consequências conhecidas

- **Uma única instância (D-9).** O cache vive na memória da aplicação. Com
  mais de uma instância rodando ao mesmo tempo, cada uma teria o seu cache, e
  uma alteração feita numa não descartaria o das outras. Por isso a aplicação
  roda como uma instância só.
- **Alterações fora da aplicação** (carga dos CSVs, alterações direto no
  banco, migrações de dados) só aparecem quando os resultados expiram, em até
  300 s, ou quando a aplicação é reiniciada (D-7).
- **Uma alteração esvazia tudo (D-4).** Depois de cada avaliação ou alteração,
  as primeiras consultas voltam a levar o tempo de hoje. Como as alterações
  são raras perto das consultas, o ganho continua grande.
- **A indicação de acerto ou falha é informativa.** Ela serve para as
  ferramentas do navegador e para os testes; a interface não a usa.

## Decisões

Tomadas antes da spec, pelo desenvolvedor. Os detalhes técnicos de cada uma
estão na seção "Decisões" do plan.

- **D-1. Onde:** só no servidor, na memória da aplicação, sem serviço externo
  e sem biblioteca nova.
  *Descartado:* um serviço de cache separado, sem ganho com uma única
  instância e o banco local; uma biblioteca de cache, por pouco código; cache
  na interface, que exigiria reescrever a busca de dados das telas.
- **D-2. O que é guardado:** as consultas do catálogo (com busca, filtros e
  ordenação) e a lista de gêneros.
  *Descartado:* detalhes, avaliações e diretores, que já são consultas
  rápidas.
- **D-3. Consultas iguais:** duas consultas são a mesma quando têm os mesmos
  valores depois de validadas, sem importar a ordem dos gêneros e dos status.
  Consultas inválidas nunca são guardadas.
- **D-4. Tudo é descartado a cada alteração:** cadastrar, atualizar ou remover
  um filme e adicionar uma avaliação descartam o cache inteiro, logo depois de
  a alteração ser gravada.
  *Descartado:* descartar só o que foi afetado. Uma avaliação nova muda a
  média e, com isso, qualquer página filtrada ou ordenada por ela; um filme
  novo desloca a paginação de todas as consultas. Descartar tudo é o único
  jeito simples de ficar sempre certo.
- **D-5. Consulta e alteração ao mesmo tempo:** uma consulta que começou antes
  de uma alteração não guarda o seu resultado, para que um resultado velho
  não seja guardado depois do descarte.
- **D-6. Indicação na resposta:** cada resposta do catálogo e da lista de
  gêneros informa se foi um acerto, uma falha ou se o cache está desligado.
- **D-7. Expiração como rede de segurança:** cada resultado vale por 300 s, com
  limite de 256 resultados guardados. A expiração cobre alterações feitas fora
  da aplicação, que não descartam o cache.
- **D-8. Configuração:** o cache pode ser desligado, e o tempo de expiração e o
  limite de resultados podem ser ajustados. Padrões: ligado, 300 s e 256.
- **D-9. Uma única instância:** o cache é da instância, então a aplicação roda
  como uma instância só (ver "Consequências conhecidas").

## Fora de escopo

- Cache na interface.
- Cache compartilhado entre instâncias.
- Instruções de cache para o navegador (a resposta não passa a ser guardada
  pelo navegador).
- Cache de detalhes, avaliações e diretores.
- Descartar só os resultados afetados por uma alteração.
- Estatísticas do cache (acertos, falhas, tamanho).
- Descartar o cache a partir da carga dos CSVs ou de migrações.
