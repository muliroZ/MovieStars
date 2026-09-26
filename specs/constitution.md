# Constituição do projeto

Este documento reúne os princípios e decisões que valem para **todas** as
features do Sistema de Avaliação de Filmes (Rocket Lab 2026). Specs e plans
de features individuais não repetem o que está aqui; eles apenas referenciam
esta constituição e registram o que for específico da feature.

Em caso de conflito, vale esta ordem: **constituição → spec → plan → código**.

---

## 1. Propósito

Módulo administrativo (frontend e backend) de um sistema de avaliação de
filmes inspirado no Letterboxd. O único usuário é o **Administrador** (até o momento), que:

- navega por um catálogo paginado de filmes e faz buscas;
- vê os detalhes de cada filme, suas avaliações e a média geral;
- cadastra, atualiza e remove filmes;
- adiciona avaliações (nota de 1 a 5 estrelas + resenha).

### Mapa de requisitos → features

| Requisito do enunciado                          | Feature                    |
|-------------------------------------------------|----------------------------|
| (pré-requisito) popular o banco com os CSVs     | `000-carga-de-dados`       |
| Catálogo paginado                               | `001-catalogo-e-busca`     |
| Busca por barra de pesquisa                     | `001-catalogo-e-busca`     |
| Detalhes do filme + lista de avaliações         | `002-detalhes-e-media`     |
| Média geral das avaliações                      | `002-detalhes-e-media`     |
| Cadastrar filme                                 | `003-gerenciar-filmes`     |
| Atualizar e remover filme                       | `003-gerenciar-filmes`     |
| Adicionar avaliação                             | `004-avaliacoes`           |

Features extras (filtros, testes de frontend, Storybook, autenticação etc.)
recebem numeração a partir de `100-`, para deixar claro que estão fora do
escopo obrigatório.

---

## 2. Processo (Spec-Driven Development)

1. **Spec antes de código.** Nenhuma feature é implementada sem `spec.md`
   com critérios de aceitação e `plan.md` aprovados pelo desenvolvedor.
2. **Etapas separadas.** Cada feature passa por: `spec.md` (o quê e por quê)
   → `plan.md` (como) → `tasks.md` (passos verificáveis) → implementação.
   Cada etapa é revisada antes de começar a próxima.
3. **A spec é a fonte da verdade.** Se a implementação revelar que algo
   precisa mudar, a spec ou o plan são atualizados **primeiro**, e só então
   o código.
4. **Escopo explícito.** Toda spec tem uma seção "Fora de escopo". O que não
   está nos critérios de aceitação não é implementado.
5. **Rastreabilidade.** Cada task referencia o critério de aceitação que
   atende. Tasks concluídas são marcadas em `tasks.md` (`- [x]`).
6. **Decisões registradas.** Toda decisão técnica não óbvia vai para a seção
   "Decisões" do `plan.md`, com a alternativa descartada e o motivo.

---

## 3. Stack (não negociável)

| Camada          | Tecnologia                                              |
|-----------------|---------------------------------------------------------|
| Backend         | Python 3.11+, FastAPI                                   |
| Validação       | Pydantic v2                                             |
| ORM             | SQLAlchemy 2.0 **assíncrono** (driver `aiosqlite`)      |
| Migrações       | Alembic                                                 |
| Banco           | SQLite (`backend/moviestars.db`)                        |
| Frontend        | Vite + React + TypeScript                               |
| Testes backend  | pytest + pytest-asyncio + httpx                         |
| Lint backend    | ruff (configuração do `pyproject.toml`)                 |

Qualquer biblioteca nova (backend ou frontend) precisa ser justificada na
seção "Decisões" do `plan.md` da feature que a introduz.

---

## 4. Decisões de domínio

Estas regras resolvem ambiguidades entre o enunciado e o modelo de dados
do repositório base. Elas se aplicam a todas as features.

### 4.1 Escala das notas

- O enunciado pede **1 a 5 estrelas**; a tabela `movie_reviews` armazena
  **0 a 10** (`nota` do tipo `Double`, com `CHECK` no banco).
- **Regra:** a API e o frontend trabalham **somente com estrelas**.
  A conversão acontece exclusivamente no backend, na camada de serviço:
  - gravação: `nota = estrelas * 2`
  - leitura: `estrelas = nota / 2`
- Entrada de novas avaliações: estrelas **inteiras de 1 a 5**.
- Avaliações importadas do CSV podem gerar valores fracionados (ex.: 3,5);
  a leitura retorna `float` e o frontend exibe meia estrela quando houver.

### 4.2 Média das avaliações

- A média é calculada **em tempo de consulta** com `AVG(movie_reviews.nota)`
  e convertida para estrelas (0 a 5, arredondada a 1 casa decimal).
- A tabela `dim_reviews` **não é fonte de verdade** para a média, pois pode
  ficar desatualizada quando novas avaliações são criadas.
- Filmes sem avaliações retornam média `null` e quantidade `0`; o frontend
  exibe "Sem avaliações".
- As notas externas de `fact_movies_performance` (TMDB, IMDb) **não** entram
  no cálculo da média do sistema.

### 4.3 Gêneros e diretor

- Gênero **não** é coluna de `dim_movies`: vem de `dim_genres` via
  `bridge_movie_genre` (um filme pode ter vários gêneros).
- Diretor **não** é coluna de `dim_movies`: é uma `DimPerson` com
  `tipo_pessoa = "Diretor"`, ligada via `bridge_movie_person`.
- Ao cadastrar ou editar um filme, gêneros são escolhidos entre os existentes
  em `dim_genres`. Diretores são buscados por nome em `dim_people`
  (`tipo_pessoa = "Diretor"`) e criados caso não existam.

### 4.4 Identificadores

- A API expõe filmes pelo `sk_movie_id` (chave primária).
- `id_filme` é obrigatório e único no banco: para filmes criados pelo
  sistema, o backend gera um UUID4 em texto. O frontend nunca envia esse
  campo.

### 4.5 Exclusão

- Remoção de filme é **definitiva** (hard delete). As chaves estrangeiras com
  `ondelete="CASCADE"` removem avaliações, vínculos e métricas associadas.
- O frontend sempre pede confirmação antes de excluir.

### 4.6 Paginação e busca

- Parâmetros: `page` (começa em 1, padrão 1) e `page_size` (padrão 20,
  máximo 100).
- Resposta paginada sempre no formato:

  ```json
  { "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0 }
  ```

- Busca pelo parâmetro `search`, sem diferenciar maiúsculas de minúsculas,
  aplicada ao título. Outras dimensões de busca (diretor, gênero) são
  definidas na spec da feature que as introduzir.
- Ordenação padrão do catálogo: título em ordem alfabética.

---

## 5. Convenções de código

### 5.1 Idioma

- **Campos do domínio** seguem os nomes do banco, em português
  (`titulo`, `sinopse`, `ano_lancamento`, `comentario`), inclusive nos
  schemas Pydantic e nos tipos TypeScript.
- **Classes, funções, variáveis e arquivos** em inglês
  (`MovieService`, `list_movies`, `MovieCard.tsx`).
- **Docstrings, comentários, mensagens de erro da API e textos da interface**
  em português (pt-BR).

### 5.2 Backend

Organização por domínio, dentro de `backend/app/<dominio>/`:

| Arquivo       | Responsabilidade                                                  |
|---------------|-------------------------------------------------------------------|
| `models.py`   | Modelos SQLAlchemy (já existente).                                |
| `schemas.py`  | Schemas Pydantic de entrada (`*Create`, `*Update`) e saída (`*Read`). |
| `service.py`  | Consultas e regras de negócio; único lugar que usa a sessão.      |
| `router.py`   | Rotas finas: recebem a requisição, chamam o serviço, devolvem o schema. |

Regras:

- Rotas registradas em `app/api/v1/router.py`, sob o prefixo `/api/v1`.
- A sessão é obtida sempre por `Depends(get_db)`.
- Todo endpoint declara `response_model` (ou anotação de retorno tipada).
- Relacionamentos são carregados **explicitamente** com `selectinload`
  (ou equivalente). Acesso preguiçoso (lazy load) a relacionamentos em
  contexto assíncrono é proibido, pois gera erro em tempo de execução.
- Commits acontecem no serviço, ao final de cada operação de escrita.
- Tabelas só são criadas ou alteradas via Alembic. É proibido usar
  `Base.metadata.create_all` na aplicação. Migrações autogeradas são
  revisadas antes de serem aplicadas.

Convenções REST:

| Situação                         | Status |
|----------------------------------|--------|
| Leitura bem-sucedida             | 200    |
| Criação                          | 201    |
| Exclusão                         | 204    |
| Recurso não encontrado           | 404    |
| Dados inválidos (Pydantic)       | 422    |
| Conflito (ex.: duplicidade)      | 409    |

Erros usam `HTTPException` com `detail` em português.

### 5.3 Frontend

Estrutura em `frontend/src/`:

| Pasta          | Responsabilidade                                               |
|----------------|----------------------------------------------------------------|
| `api/`         | Cliente HTTP e uma função por endpoint. Único lugar com `fetch`. |
| `types/`       | Tipos TypeScript que espelham os schemas do backend.           |
| `pages/`       | Uma página por rota (`CatalogPage`, `MovieDetailPage` etc.).   |
| `components/`  | Componentes reutilizáveis (`MovieCard`, `StarRating` etc.).    |
| `hooks/`       | Hooks customizados (ex.: `useDebounce`).                       |

Regras:

- TypeScript em modo `strict`; `any` é proibido.
- URL da API lida de `import.meta.env.VITE_API_URL`
  (padrão `http://localhost:8000/api/v1`).
- Navegação com `react-router-dom`.
- Toda tela que busca dados trata três estados: **carregando**, **erro** e
  **vazio**.
- Página atual e termo de busca ficam na URL (query params), para que o
  catálogo possa ser recarregado ou compartilhado sem perder o estado.
- A busca usa debounce (≈300 ms) para não disparar uma requisição a cada
  tecla.
- Layout responsivo, utilizável a partir de 360 px de largura.

---

## 6. Qualidade

### Definição de pronto

Uma feature só está concluída quando:

1. todos os critérios de aceitação da spec foram atendidos;
2. todas as tasks estão marcadas em `tasks.md`;
3. no backend: `pytest` e `ruff check .` passam sem erros;
4. no frontend: `npm run build` e `npm run lint` passam sem erros;
5. o README foi atualizado, se a feature mudar como a aplicação é executada.

### Testes

- Todo endpoint novo tem ao menos um teste do caminho feliz e um do
  principal caso de erro (ex.: 404, 422).
- Testes usam um banco isolado (SQLite em memória ou arquivo temporário),
  nunca o `moviestars.db` de desenvolvimento.
- Testes seguem o padrão existente em `backend/tests/test_app.py`
  (`httpx.AsyncClient` com `ASGITransport`).

---

## 7. Versionamento

- Uma branch por feature: `feat/001-catalogo-e-busca`.
- Commits pequenos no padrão Conventional Commits, em português:
  `feat(movies): adiciona listagem paginada`,
  `docs(specs): cria spec da feature 004`.
- Specs, plans e tasks são commitados junto com o código que descrevem.
- Arquivos `.env` e `*.db` nunca são versionados (já cobertos pelo
  `.gitignore`).

---

## 8. Alterações nesta constituição

Esta constituição pode mudar, mas toda alteração é registrada abaixo com
data e motivo, e specs afetadas são revisadas.

| Data       | Alteração          | Motivo |
|------------|--------------------|--------|
| 2026-09-25 | Versão inicial     | —      |
| 2026-09-26 | Banco renomeado de `rocketlab.db` para `moviestars.db` (seções 3 e 6) | Decisão do desenvolvedor: nome do projeto. Código e `.env.example` alinhados na feature 000. |
