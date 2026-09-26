# 000 — Carga de dados — Tasks

| Campo  | Valor                                                   |
|--------|---------------------------------------------------------|
| Status | Aprovado — em implementação                             |
| Spec   | [`spec.md`](spec.md) (aprovada)                         |
| Plan   | [`plan.md`](plan.md) (aprovado)                         |

Cada task termina com uma **verificação**. A task só é marcada `- [x]`
quando ela passa. Os comandos rodam de dentro de `backend/`.

Salvo indicação, o código vai em `backend/app/movies/load_data.py` e os
testes em `backend/tests/test_load_data.py`. Cada task de código já inclui
os testes que a cobrem.

## Fase 0 — Preparação

- [x] **T-01. Alinhar o nome do banco para `moviestars.db`** (DEC-10)
  - Alterar o padrão de `database_url` em `app/core/config.py`,
    `DATABASE_URL` em `.env.example` e `sqlalchemy.url` em `alembic.ini`.
  - Não tocar no `.env`.
  - Verificação: `grep -rn "rocketlab.db" app .env.example alembic.ini` não
    encontra nada; `.venv/bin/pytest` passa.

- [x] **T-02. Criar o esqueleto do módulo e a base dos testes** (CA-1)
  - `load_data.py` com docstring, `CSV_FILES` (os 10 arquivos na ordem de
    carga do plan), `DEFAULT_DATA_DIR` (calculado a partir do próprio
    arquivo), `LoadError` e as dataclasses `TableStats` e `LoadReport`.
  - Em `test_load_data.py`: fixture que cria um banco SQLite temporário com
    `Base.metadata.create_all` e fixture que escreve CSVs mínimos válidos,
    de 2 ou 3 linhas por arquivo, nas duas subpastas.
  - Verificação: um teste confere que `CSV_FILES` cobre exatamente as 10
    tabelas do `Base.metadata` e que `DEFAULT_DATA_DIR` termina em
    `data`; `pytest` e `ruff check .` passam.

## Fase 1 — Checagens antes de gravar

- [x] **T-03. `check_files(data_dir)`** (CA-14)
  - Confere se cada arquivo existe e se o cabeçalho tem todas as colunas da
    tabela, exceto as que têm valor padrão do banco (`created_at`). Colunas
    extras são aceitas.
  - Reúne todos os problemas numa única `LoadError`, com arquivo e colunas
    ausentes.
  - Testes: arquivo ausente; coluna ausente; coluna extra aceita; CSVs
    válidos passam.
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-04. `check_tables(conn)`** (CA-3)
  - Confere com `sqlalchemy.inspect` se as 10 tabelas existem. Se faltar
    alguma, lança `LoadError` com a orientação
    `.venv/bin/alembic upgrade head`.
  - Testes: banco vazio sem tabelas gera o erro com a mensagem; banco com o
    esquema passa.
  - Verificação: `pytest tests/test_load_data.py` passa.

## Fase 2 — Conversão e correção de valores

- [x] **T-05. `convert_value(column, raw)`** (CA-7, CA-8, CA-9, CA-13)
  - Converte conforme o tipo da coluna no models: `String` como está e sem
    `strip`, `Integer` (aceita `"2375.0"`), `Double`, `Numeric` como
    `Decimal`, e `Date` no formato `AAAA-MM-DD`.
  - Vazio vira `None`. Valor inválido sinaliza erro de conversão, e quem
    chama decide se descarta a linha ou anula o campo.
  - Testes: um caso válido e um inválido por tipo; vazio vira `None`;
    `"2375.5"` é inválido para `Integer`; texto com acentos e espaços nas
    bordas não muda; `"9.8"` continua `9.8`.
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-06. `fix_synopsis_quotes(text)`** (CA-18)
  - Aplica a regra do plan: remove a aspa inicial, remove a final só se o
    texto terminar com número ímpar de aspas e troca `""` por `"`. Retorna
    o texto e se houve correção.
  - Testes: aspas nas duas pontas; só a inicial (texto cortado); cortado
    logo após aspa interna (termina em `""`); citação no fim do texto
    (termina em `"""`); aspas legítimas no início (`"""Kill Bill"" ..."`);
    sem aspas, não muda; aspas só no meio, não muda.
  - Verificação: `pytest tests/test_load_data.py` passa.

## Fase 3 — Leitura, validação e gravação

- [x] **T-07. Ler as chaves e nomes já existentes no banco** (CA-6, CA-10)
  - Função que monta os conjuntos de chaves válidas e os mapas de
    nome → chave (`id_filme`, `nome_genero`, `nome_produtora`,
    `nome_pessoa` + `tipo_pessoa`) a partir das 4 tabelas pai, conforme a
    seção "Consultas feitas ao banco" do plan.
  - Testes: banco vazio retorna conjuntos vazios; com um registro inserido,
    ele aparece.
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-08. `load_file` para as tabelas pai** (CA-5, CA-7, CA-12, CA-13, CA-17, CA-18)
  - Leitura em fluxo com `csv.DictReader` e gravação em lotes de 5.000
    linhas com `INSERT ... ON CONFLICT DO NOTHING`.
  - Contagem de inseridas e ignoradas por `COUNT(*)` antes e depois.
  - Aplica as regras das tabelas 1 a 4 do plan: número de campos, chave
    repetida no arquivo, nome ou `id_filme` repetido no arquivo ou no banco
    com outra chave, `tipo_pessoa` válido e correção das sinopses.
  - Registra cada descarte ou campo anulado com arquivo, linha e motivo,
    e acrescenta as chaves válidas aos conjuntos.
  - Testes: título vazio descartado; tipo "Produtor" descartado; gênero
    com nome repetido descartado; data inválida vira `NULL` e a linha fica;
    linha com colunas a mais descartada; sinopse corrigida e contada.
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-09. `load_file` para as tabelas filhas** (CA-6, CA-9, CA-12)
  - Aplica as regras das tabelas 5 a 10 do plan: referências para chaves
    válidas, par repetido nas associações, `sk_movie_id` repetido em
    `dim_reviews` e `nota` entre 0 e 10.
  - Testes: associação com filme inexistente descartada; associação que
    aponta para um gênero descartado em T-08 também é descartada; nota 11
    descartada; nota `9.8` gravada como `9.8`.
  - Verificação: `pytest tests/test_load_data.py` passa.

## Fase 4 — Orquestração

- [x] **T-10. `run_load(database_url, data_dir, reset)`** (CA-1, CA-5, CA-6, CA-10, CA-15)
  - Engine síncrona (URL sem `+aiosqlite`) com `PRAGMA foreign_keys=ON` em
    cada conexão.
  - Executa `check_files`, depois `with engine.begin()`: `check_tables`,
    leitura das chaves existentes e os 10 `load_file` na ordem.
  - Retorna o `LoadReport` com o tempo total.
  - Testes:
    - carga completa em banco vazio: contagens por tabela e nenhum órfão,
      conferido com consultas `LEFT JOIN ... IS NULL`;
    - segunda execução: nada novo inserido e tudo contado como ignorado;
    - erro forçado no meio (monkeypatch em `load_file` do arquivo 7): todas
      as tabelas continuam vazias;
    - `check_files` falhando: nenhuma tabela é tocada.
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-11. `reset_tables(conn)` e opção `reset`** (CA-11)
  - Apaga as 10 tabelas na ordem inversa, dentro da mesma transação da
    carga. Só roda quando `reset=True`.
  - Testes: com dados alterados no banco (ex.: uma avaliação a mais),
    `reset=True` volta às contagens dos CSVs; sem `reset`, os dados
    existentes ficam.
  - Verificação: `pytest tests/test_load_data.py` passa.

## Fase 5 — Relatório e linha de comando

- [x] **T-12. `format_report(report)`** (CA-16, CA-17, CA-18)
  - Tabela com lidas, inseridas, ignoradas e descartadas por tabela;
    total de sinopses corrigidas; ocorrências agrupadas por arquivo e
    motivo, com até 10 números de linha e "... e mais N".
  - Testes: o texto contém os contadores; 12 ocorrências do mesmo motivo
    aparecem agrupadas, com 10 linhas listadas e "e mais 2".
  - Verificação: `pytest tests/test_load_data.py` passa.

- [x] **T-13. `main()` e `python -m app.movies.load_data`** (CA-1, CA-2, CA-3, CA-11, CA-14, CA-15)
  - `argparse` com `--data-dir` (padrão `DEFAULT_DATA_DIR`) e `--reset`.
  - Lê o `database_url` de `get_settings()` e imprime o relatório.
  - Se houver `LoadError` ou erro inesperado, imprime a mensagem e "nada
    foi gravado" e sai com código `1`. Se a carga terminar, sai com código
    `0`.
  - Testes: `main([...])` com pasta sem arquivos retorna `1`; com CSVs
    válidos retorna `0`.
  - Verificação: `.venv/bin/python -m app.movies.load_data --help` mostra
    as duas opções; `pytest` e `ruff check .` passam.

## Fase 6 — Validação com os dados reais

- [ ] **T-14. Carga real no `moviestars.db`** (CA-1, CA-5, CA-10, CA-18, RNF-1, RNF-2)
  - Rodar `.venv/bin/python -m app.movies.load_data` e conferir:
    - as contagens de inseridas batem com a tabela Q-3 da spec;
    - o relatório mostra 4.801 sinopses corrigidas;
    - o tempo total fica abaixo de 60 s.
  - Rodar de novo: tudo contado como ignorado, nada inserido.
  - Anotar o tempo medido na seção "Riscos" do plan.
  - Verificação: saídas das duas execuções coladas no resumo da task; uma
    consulta de amostra confirma sinopse corrigida e texto com acento
    preservado.

## Fase 7 — Documentação e fechamento

- [ ] **T-15. Atualizar o `README.md`** (CA-2, CA-4)
  - Em "Como executar", trocar o comentário pendente pelo comando da carga,
    entre `alembic upgrade head` e `uvicorn`.
  - Documentar `--data-dir` (padrão `data/`) e `--reset`.
  - Atualizar a tabela de status: 000 concluída.
  - Não alterar o `README-BASE.md`.
  - Verificação: seguir o README do zero, com um banco novo apontado por
    `DATABASE_URL`, deixa a API com o catálogo carregado.

- [ ] **T-16. Resolver os TODOs do `CLAUDE.md`** (CA-4)
  - Adicionar o comando da carga na seção "Comandos" e informar o caminho
    dos CSVs (`data/`) no "Mapa do código".
  - Verificação: `grep -n "TODO" CLAUDE.md` não encontra nada.

- [ ] **T-17. Definição de pronto** (constituição, seção 6)
  - `.venv/bin/pytest` e `.venv/bin/ruff check .` passam sem erros;
    `.venv/bin/ruff format .` não altera nada.
  - Todos os CA-1 a CA-18 conferidos contra os testes e a T-14.
  - Status da spec e do plan atualizado para "Concluída" e todas as tasks
    marcadas.
  - Verificação: saídas do `pytest` e do `ruff` no resumo final.

## Rastreabilidade

| CA    | Tasks                        |
|-------|------------------------------|
| CA-1  | T-02, T-10, T-13, T-14       |
| CA-2  | T-13, T-15                   |
| CA-3  | T-04, T-13                   |
| CA-4  | T-15, T-16                   |
| CA-5  | T-08, T-10, T-14             |
| CA-6  | T-07, T-09, T-10             |
| CA-7  | T-05, T-08                   |
| CA-8  | T-05                         |
| CA-9  | T-05, T-09                   |
| CA-10 | T-07, T-10, T-14             |
| CA-11 | T-11, T-13                   |
| CA-12 | T-08, T-09                   |
| CA-13 | T-05, T-08                   |
| CA-14 | T-03, T-10, T-13             |
| CA-15 | T-10, T-13                   |
| CA-16 | T-12                         |
| CA-17 | T-08, T-12                   |
| CA-18 | T-06, T-08, T-12, T-14       |
