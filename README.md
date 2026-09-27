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
feature 001 e a `0003_nome_normalizado_pessoas` da feature 003), aplique-as
antes de subir a API:

```bash
cd backend
.venv/bin/alembic upgrade head
```

A carga não precisa ser refeita: as migrações preenchem os filmes e as
pessoas que já estão no banco.

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
| 004 — Avaliações          | Não iniciada    |

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
- **Títulos com aspas extras:** 55 títulos vêm com o defeito de aspas da
  origem e aparecem no início da lista. O tratamento ficou para depois das
  funcionalidades principais.
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
