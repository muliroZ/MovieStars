# MovieStars — Sistema de Avaliação de Filmes

Módulo administrativo de um sistema de avaliação de filmes inspirado no
Letterboxd, desenvolvido para a atividade do Rocket Lab 2026. O administrador
navega pelo catálogo, busca filmes, vê detalhes e a média das avaliações,
cadastra, edita e remove filmes e adiciona avaliações (1 a 5 estrelas).

> Este é o README principal do projeto. O README original do repositório
> base da atividade foi preservado em [`README-BASE.md`](README-BASE.md).

## Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 assíncrono,
  Alembic, SQLite.
- **Frontend:** Vite, React, TypeScript (modo `strict`), React Router.

Detalhes e justificativas: [`specs/constitution.md`](specs/constitution.md).

## Estrutura

```text
.
├── backend/     # API FastAPI, modelos, migrações Alembic e testes
├── frontend/    # aplicação Vite + React + TypeScript
├── data/        # CSVs de carga inicial do catálogo
├── specs/       # constituição do projeto e specs de cada feature
├── README.md    # este arquivo
└── README-BASE.md
```

## Como executar

### Backend

Requer Python 3.11 ou superior.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head          # cria as tabelas
.venv/bin/python -m app.movies.load_data # carrega os CSVs de data/ (~35 s)
.venv/bin/uvicorn app.main:app --reload # API em http://localhost:8000/docs
```

O banco é o arquivo `backend/moviestars.db`, definido por `DATABASE_URL` no
`.env`. Depois da carga, ele ocupa cerca de 550 MB e não é versionado.

#### Cache de consultas

A API guarda em memória, por até 5 minutos, as respostas do catálogo
(`GET /movies`, com busca, filtros e ordenação) e da lista de gêneros
(`GET /genres`). Uma consulta repetida, como a última página ordenada pela
média, cai de cerca de 400 ms para menos de 2 ms.

- Cadastrar, editar ou remover um filme, ou adicionar uma avaliação, esvazia
  o cache inteiro: a próxima consulta já mostra o dado novo.
- Alterações feitas fora da API (a carga dos CSVs, SQL direto no banco,
  migrações de dados) só aparecem quando o cache expira, ou ao reiniciar a
  API.
- As respostas das duas rotas trazem o cabeçalho `X-Cache`: `HIT` (veio do
  cache), `MISS` (calculada agora) ou `BYPASS` (cache desligado). Ele aparece
  na aba Rede das ferramentas do navegador.
- O cache fica na memória do processo: rode a API com um único worker (o
  padrão do `uvicorn`); não use `--workers` maior que 1.

| Variável            | Padrão | O que faz                                   |
|---------------------|--------|---------------------------------------------|
| `CACHE_ENABLED`     | `true` | Liga ou desliga o cache                     |
| `CACHE_TTL_SECONDS` | `300`  | Tempo, em segundos, que cada resposta vale  |
| `CACHE_MAX_ENTRIES` | `256`  | Respostas guardadas; ao passar do limite, sai a menos usada |

As variáveis são opcionais: sem elas no `.env`, valem os padrões.

Testes e lint:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

### Frontend

Com a API rodando (seção anterior), em outro terminal:

```bash
cd frontend
bun install     # instala também o react-router-dom
bun run dev     # http://localhost:5173
```

O frontend procura a API em `http://localhost:8000/api/v1`. Para usar outro
endereço, crie `frontend/.env.local` com `VITE_API_URL=<endereço>`.

Checagem de tipos, build e lint:

```bash
bun run build
bun run lint
```

### Depois de atualizar o repositório

Se novas migrações chegarem (por exemplo, a `0002_titulo_normalizado` da
feature 001, a `0003_nome_normalizado_pessoas` da feature 003, a
`0004_indices_filtros` da feature 100 e a `0005_titulos_com_aspas`), aplique-as
antes de subir a API:

```bash
cd backend
.venv/bin/alembic upgrade head
```

A carga não precisa ser refeita: as migrações preenchem os filmes e as
pessoas que já estão no banco (a 0004 só cria índices, e a 0005 corrige os
55 títulos com aspas).

## Dados

Os CSVs do catálogo estão versionados em `data/`:

- `data/bases_atv_dev1/`: filmes, gêneros, pessoas, produtoras e resumo de
  avaliações;
- `data/bases_atv_dev_2/`: associações filme–gênero/pessoa/produtora,
  métricas de desempenho e avaliações individuais.

São cerca de 1,7 milhão de linhas no total.

### Carga no banco

De dentro de `backend/`, depois de `alembic upgrade head`:

```bash
.venv/bin/python -m app.movies.load_data                     # usa a pasta data/
.venv/bin/python -m app.movies.load_data --data-dir /outra/pasta
.venv/bin/python -m app.movies.load_data --reset             # apaga e recarrega tudo
```

| Opção        | Padrão                         | Efeito                                                   |
|--------------|--------------------------------|----------------------------------------------------------|
| `--data-dir` | `data/` na raiz do repositório | Pasta com as subpastas `bases_atv_dev1/` e `bases_atv_dev_2/`. |
| `--reset`    | desligado                      | Apaga os dados das 10 tabelas antes de carregar.         |

Como a carga se comporta:

- **Pode ser repetida:** registros que já existem no banco são mantidos e
  contados como "ignorados"; nada é duplicado.
- **Tudo ou nada:** a carga roda numa única transação. Se algo falhar, o
  banco volta ao estado anterior, inclusive quando `--reset` foi usado.
- **Não cria tabelas:** se as migrações não tiverem sido aplicadas, a carga
  para e pede para rodar `alembic upgrade head`.
- **Relatório:** no final, mostra por tabela as linhas lidas, inseridas,
  ignoradas e descartadas, além de cada linha descartada ou campo anulado,
  com o arquivo, o número da linha e o motivo.

Especificação completa: [`specs/features/000-carga-de-dados/`](specs/features/000-carga-de-dados/).

## Processo de desenvolvimento

O projeto segue Spec-Driven Development: cada feature vive em
`specs/features/NNN-nome/` e passa por `spec.md` → `plan.md` → `tasks.md` →
implementação, com revisão ao final de cada etapa.

| Feature                   | Status          |
|---------------------------|-----------------|
| 000 — Carga de dados      | Concluída       |
| 001 — Catálogo e busca    | Concluída       |
| 002 — Detalhes e média    | Concluída       |
| 003 — Gerenciar filmes    | Concluída       |
| 004 — Avaliações          | Concluída       |
| 100 — Filtros do catálogo | Concluída       |
| 101 — Cache de consultas  | Concluída       |

## Decisões

### Domínio (valem para todo o projeto)

Resumo; o texto completo está na seção 4 da
[constituição](specs/constitution.md).

- **Notas:** o banco guarda 0–10; a API e a interface usam 1–5 estrelas. A
  conversão acontece só no backend.
- **Média:** calculada na consulta a partir das avaliações individuais; a
  tabela de resumo `dim_reviews` não é usada para exibir médias.
- **Gênero e diretor:** vêm de tabelas de associação, não de colunas do filme.
- **Exclusão de filme:** definitiva, removendo avaliações e vínculos.

### Carga de dados (feature 000)

- **Dados gravados como estão:** inconsistências dos CSVs (ex.: duração 0,
  resumo de avaliações divergente) vão para o banco sem correção. Só é
  descartado ou anulado o que o banco não aceita.
- **Exceção, aspas nas sinopses:** 4.801 sinopses vêm com aspas de escape
  duplicadas; a carga remove as aspas extras. 3.312 delas vêm cortadas na
  origem e não há como recuperar o texto.
- **Exceção, aspas nos títulos:** 55 títulos vêm com o mesmo defeito. A
  carga aplica a mesma regra e põe a primeira letra em maiúscula, que a
  origem deixou minúscula (ex.: `Floyd "money" Mayweather`). Dois títulos
  continuam entre aspas porque elas fazem parte do título (`"Blessed"`,
  `"Truelove: The Film"`), e dois ficam com uma aspa sem par, como na origem.
  Nos bancos já carregados, a correção vem pela migração 0005.
- **Duração 0:** 10.160 filmes têm duração 0; a interface exibe "não
  informada".
- **Datas das avaliações importadas:** o CSV não tem data, então todas
  recebem a data da carga.
- **Script síncrono:** a carga usa o SQLAlchemy síncrono, porque é um
  comando rodado uma vez pelo terminal e não atende requisições
  simultâneas. A API continua assíncrona.
- **Validação antes de gravar:** regras que o banco recusaria (tipo de
  pessoa, nota entre 0 e 10, referências a outras tabelas, nomes repetidos)
  são conferidas em Python. Assim, uma linha inválida é descartada sem
  abortar a transação inteira.
- **Nome do banco:** `moviestars.db` (constituição, seção 8).

### Catálogo e busca (feature 001)

- **Tela inicial:** catálogo paginado (20 por página) com busca pelo título.
  Página e busca ficam na URL, então recarregar, compartilhar e usar o
  voltar do navegador funcionam.
- **Cartão:** pôster (ou imagem padrão), título, ano, média em estrelas com
  a quantidade de avaliações, até 3 gêneros ("+N") e até 2 diretores ("e
  mais N"). Quando falta uma informação, o cartão mostra um texto como "Sem
  gênero".
- **Busca e ordem sem acentos:** "acao" encontra "Ação", e "À La Recherche"
  fica junto dos títulos com "A". Para isso, `dim_movies` ganhou a coluna
  `titulo_normalizado` (migração 0002), com índice. Cada página responde em
  menos de 40 ms com o catálogo completo.
- **Busca literal:** `%` e `_` são tratados como texto comum.
- **Títulos com aspas extras:** 55 títulos vinham com o defeito de aspas da
  origem e abriam a lista. Desde 2026-09-27 eles são corrigidos (ver "Carga
  de dados"); a lista agora começa por `"Blessed"` e `"Truelove: The Film"`,
  que têm aspas na origem.
- **Paginação:** primeira, anterior, próxima e última, com "Página X de Y".
  Em telas estreitas, os botões mostram só os símbolos.
- **Responsivo:** a partir de 360 px. O cabeçalho com a busca fica fixo no
  topo só em telas largas.

### Detalhes do filme e média (feature 002)

- **Página `/filmes/<chave>`:** pôster, título, ano, data, duração, status,
  gêneros, sinopse, média em estrelas, equipe (Direção, Roteiro, Elenco),
  produtoras, dados financeiros e avaliações. Chave inexistente mostra
  "Filme não encontrado".
- **API:** `GET /api/v1/movies/{sk_movie_id}` (detalhes) e
  `GET /api/v1/movies/{sk_movie_id}/reviews` (avaliações, 10 por página).
  As duas respondem `404` para filme inexistente.
- **Média igual ao catálogo:** as duas telas usam o mesmo cálculo no
  backend.
- **Listas longas:** até 10 nomes, com "Mostrar todos (N)". Isso cobre
  99,5% dos filmes sem botão; o maior caso tem 88 diretores.
- **Dinheiro em real e dólar,** como vem nos dados. O lucro só aparece
  quando orçamento e receita existem (nos dados, sem os dois ele vale
  −orçamento ou 0, o que sugeriria prejuízos que não aconteceram).
  Prejuízo aparece em vermelho e com a palavra "prejuízo".
- **Avaliações:** das mais recentes para as mais antigas, com a data, 10 por
  vez com "Mostrar mais avaliações". As importadas mostram todas a data da
  carga, porque o CSV não tem data.
- **Datas e fuso:** o banco grava `created_at` em UTC; a API envia com `Z` e
  a interface mostra no horário local. A data de lançamento é formatada a
  partir do texto, sem passar por `new Date`, para não voltar um dia no fuso
  do Brasil.
- **Voltar ao catálogo:** retorna à mesma página e busca de onde se saiu.
- **Formatações compartilhadas** ficam em `frontend/src/utils/format.ts`
  (pasta acrescentada à constituição).

### Gerenciar filmes (feature 003)

- **Onde:** "Novo filme" no cabeçalho do catálogo; "Editar" e "Excluir" na
  página de detalhes.
- **Campos:** título, ano e status são obrigatórios; também data de
  lançamento, duração, sinopse, URLs do pôster e da imagem de fundo, gêneros
  e diretores. Roteiro, elenco, produtoras e dados financeiros continuam
  vindo só da carga.
- **Validação igual na tela e na API:** o formulário avisa antes de enviar,
  e a API recusa com as mesmas mensagens em português. Os erros 422 de toda
  a API passaram a vir em português (`backend/app/core/errors.py`).
- **Gêneros e diretores pelo nome:** os nomes são únicos no banco. Gêneros só
  entre os existentes. Diretores: sugestões sem acentos enquanto se digita;
  um nome digitado reaproveita o diretor existente só se for idêntico, senão
  cria um diretor novo (marcado como "novo" no formulário).
- **Busca de diretores rápida:** `dim_people` ganhou `nome_normalizado` com
  índice (migração 0003); cada busca leva poucos milissegundos entre os
  65.200 diretores.
- **Edição:** troca só os diretores do filme, preservando roteiristas e
  elenco, e recalcula o título normalizado para a busca e a ordem.
- **Remoção definitiva:** pede confirmação mostrando quantas avaliações serão
  apagadas; o banco apaga em cascata avaliações, vínculos e métricas.
  Pessoas, gêneros e produtoras continuam cadastrados.
- **Mensagens de sucesso** ("Filme cadastrado.", "Filme atualizado.", "Filme
  excluído.") aparecem no topo e somem em 5 s.

### Adicionar avaliações (feature 004)

- **Onde:** formulário "Adicionar avaliação" na seção de avaliações da
  página de detalhes, acima da lista.
- **Campos:** nome de quem avalia (até 120 caracteres), nota de 1 a 5
  estrelas inteiras e comentário (até 1.000 caracteres, com contador). Todos
  obrigatórios; a mesma pessoa pode avaliar o mesmo filme mais de uma vez.
- **Escala:** a nota é gravada como `estrelas × 2` (4 estrelas → 8) e exibida
  de volta em estrelas. As duas conversões ficam só no backend.
- **API:** `POST /api/v1/movies/{sk_movie_id}/reviews` (201), com as mesmas
  validações e mensagens em português do formulário; `404` para filme
  inexistente. Qualquer filme aceita avaliações, inclusive os não lançados.
- **Depois de enviar:** a avaliação aparece no topo da lista (que volta às 10
  mais recentes), o total e a média do topo da página atualizam sem a página
  recarregar, e aparece "Avaliação adicionada.".
- **Limitações aceitas:** o resumo `dim_reviews` não é atualizado (a média
  vem sempre das avaliações individuais); a data de criação tem precisão de
  1 segundo, então duas avaliações do mesmo filme criadas no mesmo segundo
  podem aparecer fora de ordem.

### Filtros e ordenação do catálogo (feature 100)

- **Onde:** uma barra acima da grade, com o botão "Filtros (N)", o seletor
  "Ordenar por" e o botão "Inverter". O painel de filtros começa fechado, e
  abrir ou fechar não muda a lista.
- **Filtros:** gêneros (com a chave "Qualquer um"/"Todos"), ano "de" e
  "até" (inclusivos, com espera de 400 ms), status, avaliações ("Todos",
  "Com avaliação", "Sem avaliação") e mínimo de estrelas de 1 a 5. Valem na
  hora, somam com a busca pelo título e voltam para a página 1. "Limpar
  filtros" mantém a busca e a ordenação.
- **Mínimo de estrelas pela média exibida:** um filme mostrado com "4,0"
  entra em "4 estrelas ou mais", mesmo com média exata 3,96. Filmes sem
  avaliação não entram, e "Sem avaliação" desabilita as estrelas.
- **Ordenação:** título (A–Z, padrão), ano (mais recentes), média de
  estrelas (maiores) e quantidade de avaliações (mais avaliados); "Inverter"
  troca a direção. Filmes sem ano ou sem avaliação ficam sempre no fim;
  empates vão pelo título e pelo ano.
- **Tudo no endereço:** filtros e ordenação ficam na URL com os mesmos nomes
  da API (`genre`, `genre_mode`, `year_min`, `year_max`, `status`,
  `reviews`, `min_stars`, `sort`, `reverse`), sem os valores padrão.
  Recarregar e o voltar do navegador funcionam; valores inválidos são
  ignorados, e gêneros inexistentes saem da URL.
- **Desempenho:** a média e a quantidade de avaliações são calculadas na hora
  (`AVG` sobre `movie_reviews`) e só entram na consulta quando o filtro ou a
  ordenação precisam delas. A migração 0004 criou dois índices
  (`movie_reviews (sk_movie_id, nota)` e `bridge_movie_genre (sk_genre_id,
  sk_movie_id)`), e a página ordena as chaves antes de carregar os filmes. O
  pior caso medido foi 456 ms.

### Cache de consultas (feature 101)

- **Onde:** só no backend, na memória do processo, sem serviço externo nem
  biblioteca nova (uma classe pequena em `backend/app/core/cache.py`). Redis,
  `cachetools` e cache no frontend foram descartados.
- **O que é guardado:** as respostas de `GET /movies` e `GET /genres`.
  Detalhes, avaliações e diretores já são rápidos e ficam de fora.
- **Consultas iguais:** a chave vem dos parâmetros já validados, sem importar
  a ordem dos gêneros e dos status; requisições inválidas (422) nunca são
  guardadas.
- **Tudo é descartado a cada alteração:** uma avaliação nova muda a média de
  qualquer página filtrada ou ordenada por ela, e um filme novo desloca a
  paginação de todas as consultas. Descartar só o afetado seria mais
  complexo e fácil de errar.
- **Sem resultado velho:** uma consulta que começou antes de uma alteração e
  terminou depois dela não guarda o seu resultado (contador de geração).
- **Expiração de 5 minutos e limite de 256 respostas:** a expiração cobre as
  alterações feitas fora da API.
