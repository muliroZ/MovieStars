# 001 — Catálogo e busca

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Concluída                                              |
| Depende de     | 000 (catálogo carregado no banco)                      |
| Bloqueia       | 002 (o cartão leva aos detalhes do filme)              |
| Referências    | `specs/constitution.md` (seções 1, 4.1, 4.2, 4.3, 4.6, 5.3) |

## Contexto

O administrador precisa navegar por um catálogo de cerca de 95 mil filmes e
encontrar um filme específico pelo título. Esta feature entrega a tela
inicial da aplicação: uma lista paginada de cartões de filmes, com uma barra
de busca.

A constituição já define a paginação (seção 4.6): página inicial 1, 20 itens
por página e no máximo 100. Também já define a busca pelo título, sem
diferenciar maiúsculas de minúsculas, e a ordem alfabética padrão. Esta spec
detalha o que cada cartão mostra, como a busca e a ordenação se comportam e
como a tela reage a cada situação.

## Histórias de usuário

- **H-1.** Como administrador, quero navegar pelo catálogo página a página,
  para ter uma visão geral dos filmes cadastrados.
- **H-2.** Como administrador, quero buscar um filme digitando parte do
  título, para encontrá-lo sem percorrer milhares de páginas.
- **H-3.** Como administrador, quero ver em cada cartão as informações
  principais do filme, para identificá-lo sem abrir os detalhes.
- **H-4.** Como administrador, quero recarregar ou compartilhar o endereço da
  página e voltar exatamente à mesma página e busca.

## Critérios de aceitação

### Listagem e paginação

- **CA-1** (H-1). A tela inicial mostra o catálogo em cartões, 20 por página,
  começando na página 1.
- **CA-2** (H-1). A ordem é alfabética pelo título, sem diferenciar
  maiúsculas, minúsculas nem acentos. Por exemplo, "À La Recherche" fica
  junto dos títulos que começam com "A". Filmes com o mesmo título ficam em
  ordem de ano de lançamento, do mais antigo para o mais recente. A ordem é
  sempre a mesma entre uma consulta e outra, então nenhum filme se repete ou
  some ao trocar de página.
- **CA-3** (H-1). A tela mostra o total de filmes (ex.: "95.645 filmes"), a
  página atual e o total de páginas (ex.: "Página 3 de 4.783").
- **CA-4** (H-1). Há controles para ir à primeira página, à anterior, à
  próxima e à última. Na primeira página, "primeira" e "anterior" ficam
  desabilitados; na última, "próxima" e "última" ficam desabilitados.
- **CA-5** (H-1). Ao trocar de página, a tela volta ao topo da lista.

### Cartão do filme

- **CA-6** (H-3). Cada cartão mostra:
  - o pôster; sem pôster, ou se a imagem não carregar, aparece uma imagem
    padrão;
  - o título, exatamente como está no banco;
  - o ano de lançamento, ou "Ano não informado" quando não houver;
  - a média das avaliações em estrelas, com uma casa decimal (ex.: 3,5), e a
    quantidade de avaliações (ex.: "12 avaliações"); sem avaliações, aparece
    "Sem avaliações";
  - até 3 gêneros em ordem alfabética, seguidos de "+N" quando houver mais;
    sem gênero, aparece "Sem gênero";
  - até 2 diretores, seguidos de "e mais N" quando houver mais; sem diretor,
    aparece "Diretor não informado".
- **CA-7** (H-3). A média segue a constituição: é calculada a partir das
  avaliações individuais, e não do resumo em `dim_reviews`, na escala de 0 a
  5 estrelas, arredondada a 1 casa decimal (seção 4.2).
- **CA-8** (H-3). Títulos longos (até 151 caracteres nos dados atuais) não
  quebram o layout do cartão. Eles são cortados com reticências, e o título
  completo aparece ao passar o mouse.
- **CA-9** (H-3). Clicar no cartão leva à página de detalhes do filme. A
  página de detalhes em si é entregue pela feature 002.

### Busca

- **CA-10** (H-2). A barra de busca procura o termo em **qualquer parte** do
  título (ex.: "ring" encontra "Rings" e "The Lord of the Rings").
- **CA-11** (H-2). A busca não diferencia maiúsculas, minúsculas nem
  acentos: "acao", "AÇÃO" e "Ação" encontram os mesmos filmes.
- **CA-12** (H-2). Espaços no início e no fim do termo são ignorados. Um
  termo vazio, ou só com espaços, mostra o catálogo completo.
- **CA-13** (H-2). Caracteres especiais no termo, como `%`, `_`, aspas e
  apóstrofos, são tratados como texto comum (ex.: "100%" encontra só títulos
  que contêm "100%").
- **CA-14** (H-2). A busca acontece enquanto o administrador digita, sem
  precisar apertar Enter, depois de uma breve pausa na digitação (cerca de
  300 ms, constituição, seção 5.3).
- **CA-15** (H-2). Os resultados da busca seguem a mesma ordem e a mesma
  paginação do catálogo (CA-2 a CA-4). A tela mostra o total de resultados
  (ex.: "37 filmes encontrados para "ring"").
- **CA-16** (H-2). Mudar o termo de busca volta para a página 1.
- **CA-17** (H-2). Há um jeito visível de limpar a busca e voltar ao
  catálogo completo.

### Endereço da página

- **CA-18** (H-4). A página atual e o termo de busca ficam no endereço da
  página. Recarregar ou abrir o mesmo endereço em outra aba mostra a mesma
  página e a mesma busca.
- **CA-19** (H-4). Os botões voltar e avançar do navegador percorrem as
  páginas e buscas visitadas.
- **CA-20** (H-4). Um número de página inválido no endereço (0, negativo ou
  texto) é tratado como página 1.

### Estados da tela

- **CA-21**. Enquanto os dados carregam, a tela mostra um indicador de
  carregamento.
- **CA-22**. Se a consulta falhar (ex.: API fora do ar), a tela mostra uma
  mensagem de erro em português e um botão "Tentar novamente".
- **CA-23**. Uma busca sem resultados mostra "Nenhum filme encontrado para
  "<termo>"" e o jeito de limpar a busca (CA-17).
- **CA-24**. Uma página além da última mostra "Esta página não existe" e um
  link para a página 1.

### Validação das consultas

- **CA-25**. Consultas com página menor que 1 ou com tamanho de página fora
  de 1 a 100 são recusadas com erro de validação (constituição, seção 5.2).
- **CA-26**. Termos de busca com mais de 200 caracteres são recusados com
  erro de validação. O campo de busca da interface não deixa digitar além
  desse limite.

### Layout

- **CA-27**. A tela é utilizável a partir de 360 px de largura: a grade de
  cartões se ajusta à largura disponível e os controles de paginação
  continuam acessíveis (constituição, seção 5.3).

## Casos de borda

| Situação                                              | Comportamento esperado                                      |
|-------------------------------------------------------|-------------------------------------------------------------|
| Catálogo vazio (banco sem carga)                      | Mensagem "Nenhum filme cadastrado"; sem controles de paginação. |
| Busca com um único resultado                          | Mostra "1 filme encontrado"; paginação com "Página 1 de 1". |
| Termo de busca só com espaços                         | Mesmo que termo vazio (CA-12).                              |
| Termo com `%` ou `_`                                  | Tratado como texto comum (CA-13).                           |
| Termo com acento ou maiúsculas diferentes do título   | Encontra o título (CA-11).                                  |
| Página além da última no endereço                     | "Esta página não existe" e link para a página 1 (CA-24).    |
| Página inválida no endereço (`page=0`, `page=abc`)    | Tratada como página 1 (CA-20).                              |
| URL do pôster quebrada ou sem internet                | Imagem padrão (CA-6).                                       |
| Filme com 11 gêneros                                  | 3 gêneros e "+8" (CA-6).                                    |
| Filme com mais de 2 diretores                         | 2 diretores e "e mais N" (CA-6).                            |
| Filme sem avaliações                                  | "Sem avaliações" (CA-6).                                    |
| Média com meia estrela (ex.: 3,5)                     | Exibida com meia estrela (constituição, seção 4.1).         |
| Filmes com o mesmo título                             | Diferenciados pelo ano e ordenados por ele (CA-2, CA-6).    |
| Filme com ano futuro (status Planejado etc.)          | Aparece normalmente, com o ano cadastrado.                  |

## Requisitos não funcionais

- **RNF-1.** Com o catálogo completo carregado (95.645 filmes), cada página
  do catálogo ou da busca responde em até 1 s numa máquina de
  desenvolvimento comum. *(A validar na implementação.)*
- **RNF-2.** A busca não dispara uma consulta a cada tecla (CA-14).

## Consequências conhecidas

- **Títulos com aspas extras.** 55 títulos têm o mesmo defeito de aspas das
  sinopses (ex.: `"""blessed"""`). Eles são exibidos como estão (D-1) e,
  como começam com aspas, aparecem no início da ordem alfabética.
- **Títulos com espaço no início.** 3 títulos começam com espaço (spec 000,
  D-3) e também aparecem no início da ordem.
- **Títulos que começam com símbolo ou dígito** (263 e 1.400) aparecem
  antes das letras, como é comum na ordem alfabética.
- **Gêneros em inglês.** Os nomes dos gêneros estão em inglês nos dados
  (ex.: "Science Fiction", "Tv Movie") e são exibidos assim, embora o resto
  da interface esteja em português (spec 000, D-4).
- **Pôsteres dependem de internet.** As imagens vêm de endereços externos
  (TMDB). Sem internet, todos os cartões mostram a imagem padrão.
- **Filmes não lançados.** 1.341 filmes estão com status Planejado, Em
  Produção ou Pós-Produção e aparecem no catálogo como os demais.

## Decisões

- **D-1.** Os 55 títulos com defeito de aspas são mantidos como estão (spec
  000, D-4). *Descartado:* estender a correção do CA-18 da spec 000 aos
  títulos.
- **D-2.** O cartão mostra média de estrelas, gêneros e diretores, além de
  pôster, título e ano. A duração não aparece no cartão.
- **D-3.** A busca procura só no título, como na constituição. *Descartado:*
  buscar também por diretor, que fica para uma possível feature de filtros
  (100+).
- **D-4.** Busca e ordenação ignoram maiúsculas, minúsculas e acentos.
  *Descartado:* seguir o comportamento padrão do banco, que põe títulos
  acentuados depois do Z e não encontra "ação" buscando "AÇÃO".

### Propostas desta spec (confirmar na revisão)

- **D-5.** Limites no cartão: até 3 gêneros ("+N") e até 2 diretores ("e
  mais N"). Nos dados, 96% dos filmes têm até 3 gêneros e 90% têm 1
  diretor.
- **D-6.** Ausências aparecem com texto explícito ("Sem gênero", "Diretor
  não informado", "Ano não informado"), em vez de a informação sumir do
  cartão. Assim o administrador vê o que está faltando no cadastro.
- **D-7.** Paginação com primeira, anterior, próxima e última e o indicador
  "Página X de Y", sem lista de números de página. Com mais de 4 mil
  páginas, uma lista de números ajuda pouco.
- **D-8.** O tamanho da página é fixo em 20 na interface. A API aceita
  outros tamanhos (constituição), mas a tela não oferece essa escolha.
- **D-9.** O termo de busca pode ter até 200 caracteres (CA-26). O maior
  título atual tem 151.
- **D-10.** Página além da última mostra uma mensagem com link para a
  página 1 (CA-24), em vez de redirecionar sozinha para a última página.

## Fora de escopo

- Página de detalhes do filme (feature 002); aqui só existe o link (CA-9).
- Cadastrar, editar ou remover filmes (feature 003) e adicionar avaliações
  (feature 004).
- Busca por diretor, gênero, ano ou outros campos; filtros e ordenações
  alternativas (possível feature 100+).
- Escolher o tamanho da página na interface (D-8).
- Rolagem infinita.
- Destacar o termo buscado no título dos resultados.
- Traduzir os nomes dos gêneros.
- Corrigir títulos, nomes ou outros dados (D-1; spec 000, D-4).
