# 000 — Carga de dados — Plan

| Campo       | Valor                                       |
|-------------|---------------------------------------------|
| Status      | Aprovado                                    |
| Spec        | [`spec.md`](spec.md) (aprovada)             |
| Referências | `specs/constitution.md` (seções 3, 4.1, 5.2, 6) |

## Visão geral

A carga é um **script de linha de comando** do backend, sem endpoint HTTP.
Ele lê os dez CSVs em sequência, valida e converte cada linha em Python e
grava tudo no banco em **uma única transação**. No fim, imprime um
relatório.

```text
checar arquivos e colunas (CA-14) ─► checar tabelas (CA-3) ─► [--reset: apagar tudo] (CA-11)
      │
      ▼
para cada CSV, na ordem das dependências:
   ler linha ─► validar/converter ─► lote de 5.000 ─► INSERT ... ON CONFLICT DO NOTHING
      │
      ▼
commit (ou rollback total em caso de erro, CA-15) ─► relatório (CA-16, CA-17)
```

## Comando

Executado de dentro de `backend/`, como o Alembic e o uvicorn, porque o
`.env` é lido do diretório atual:

```bash
.venv/bin/python -m app.movies.load_data                 # usa ../data (CA-2)
.venv/bin/python -m app.movies.load_data --data-dir /caminho/para/csvs
.venv/bin/python -m app.movies.load_data --reset         # apaga e recarrega (CA-11)
```

| Opção        | Padrão              | Efeito                                                      |
|--------------|---------------------|-------------------------------------------------------------|
| `--data-dir` | `data/` na raiz do repositório | Pasta com as subpastas `bases_atv_dev1/` e `bases_atv_dev_2/`. |
| `--reset`    | desligado           | Apaga os dados das 10 tabelas antes de carregar, na mesma transação. |

O caminho padrão é calculado a partir do próprio arquivo do script, e não
do diretório atual. Assim ele funciona de qualquer lugar.

Códigos de saída: `0` quando a carga termina (mesmo com linhas
descartadas); `1` quando ela é interrompida (CA-3, CA-14, CA-15).

## Arquivos e ordem de carga

A ordem segue as chaves estrangeiras: primeiro as tabelas das quais outras
dependem.

| # | Arquivo (relativo a `--data-dir`)               | Tabela                    |
|---|-------------------------------------------------|---------------------------|
| 1 | `bases_atv_dev1/dim_movies.csv`                 | `dim_movies`              |
| 2 | `bases_atv_dev1/dim_genres.csv`                 | `dim_genres`              |
| 3 | `bases_atv_dev1/dim_companies.csv`              | `dim_companies`           |
| 4 | `bases_atv_dev1/dim_people.csv`                 | `dim_people`              |
| 5 | `bases_atv_dev_2/bridge_movie_genre.csv`        | `bridge_movie_genre`      |
| 6 | `bases_atv_dev_2/bridge_movie_company.csv`      | `bridge_movie_company`    |
| 7 | `bases_atv_dev_2/bridge_movie_person.csv`       | `bridge_movie_person`     |
| 8 | `bases_atv_dev_2/fact_movies_performance.csv`   | `fact_movies_performance` |
| 9 | `bases_atv_dev1/dim_reviews.csv`                | `dim_reviews`             |
| 10| `bases_atv_dev_2/movies_reviews.csv`            | `movie_reviews`           |

O `--reset` apaga na ordem inversa (10 → 1).

## Validação e conversão

### Colunas esperadas (CA-14)

As colunas de cada arquivo são **as colunas da tabela no `models.py`**,
exceto as que o banco preenche sozinho (`movie_reviews.created_at`).
Antes de gravar qualquer dado, o script abre os dez arquivos e lê só o
cabeçalho. Se algum arquivo faltar ou não tiver alguma coluna, a execução
para com uma mensagem por arquivo:

```text
Erro: bases_atv_dev_2/movies_reviews.csv não tem as colunas: nota, comentario
```

Colunas extras no cabeçalho são ignoradas. A ordem das colunas não
importa, porque cada linha é lida pelo nome da coluna (`csv.DictReader`).

### Tabelas existentes (CA-3)

Antes da carga, o script confere se as 10 tabelas existem no banco. Se
faltar alguma:

```text
Erro: o banco não tem as tabelas da aplicação. Rode as migrações primeiro:
  .venv/bin/alembic upgrade head
```

### Conversão por tipo de coluna (CA-7, CA-8, CA-9, CA-13)

A conversão é decidida pelo tipo da coluna no `models.py`:

| Tipo no models   | Conversão                                   | Exemplo                 |
|------------------|---------------------------------------------|-------------------------|
| `String`         | Texto como está, sem `strip` (D-3)          | `" Título"` → `" Título"` |
| `Integer`        | Número inteiro; aceita casa decimal zerada  | `"2375.0"` → `2375`     |
| `Double`         | Número decimal                              | `"4.966"` → `4.966`     |
| `Numeric`        | `Decimal`                                   | `"25000000.0"`          |
| `Date`           | Formato `AAAA-MM-DD`                        | `"2017-02-01"`          |

- Célula vazia → `None` (CA-7).
- Valor que não converte:
  - coluna obrigatória (`NOT NULL`) → linha descartada (CA-12);
  - coluna opcional → gravada como `None` e registrada no relatório (CA-13).
- Notas são gravadas como estão, sem conversão para estrelas (CA-9).

### Regras além do tipo (CA-6, CA-12, CA-18)

São verificadas em Python **antes** do insert. Se o banco recusasse uma
linha, o erro abortaria a transação inteira (ver decisão DEC-6).

| Tabela              | Regra                                                         | Se falhar |
|---------------------|---------------------------------------------------------------|-----------|
| Todas               | Número de campos da linha igual ao do cabeçalho               | Descarta  |
| Todas               | Chave primária não repetida dentro do próprio arquivo         | Descarta (fica a primeira) |
| `dim_movies`        | `id_filme` não repetido no arquivo nem no banco (com outra chave) | Descarta |
| `dim_movies`        | `sinopse` começando com aspas → correção do CA-18             | Corrige e conta |
| `dim_genres`        | `nome_genero` não repetido (arquivo ou banco, com outra chave) | Descarta |
| `dim_companies`     | `nome_produtora` não repetido (idem)                          | Descarta  |
| `dim_people`        | `tipo_pessoa` em Ator, Diretor, Roteirista                    | Descarta  |
| `dim_people`        | par `nome_pessoa` + `tipo_pessoa` não repetido (idem)         | Descarta  |
| `dim_reviews`       | `sk_movie_id` não repetido no arquivo                         | Descarta  |
| `movie_reviews`     | `nota` entre 0 e 10                                           | Descarta  |
| Filhas (5 a 10)     | `sk_movie_id`, `sk_genre_id`, `sk_company_id` e `sk_person_id` apontam para chave válida | Descarta |

Uma **chave válida** é uma chave que já existia no banco antes da carga ou
que veio de uma linha válida do CSV pai. Uma linha pai descartada leva
junto as filhas que apontam para ela (CA-6).

Correção do CA-18, função `fix_synopsis_quotes(texto)`:

```text
se o texto começa com '"':
    remove a primeira aspa
    se o texto termina com um número ímpar de aspas seguidas:
        remove a última aspa          # 1 = fechamento; 3 = "" interno + fechamento
    troca cada '""' por '"'           # 2 no fim = "" interno de texto cortado
```

### Consultas feitas ao banco

1. **Antes da carga**, para montar os conjuntos de chaves válidas e
   detectar conflitos de nome, o script lê:
   - `dim_movies`: `sk_movie_id` e `id_filme`;
   - `dim_genres`: `sk_genre_id` e `nome_genero`;
   - `dim_companies`: `sk_company_id` e `nome_produtora`;
   - `dim_people`: `sk_person_id`, `nome_pessoa` e `tipo_pessoa`.

   Com o banco vazio, essas leituras não trazem nada.
2. **Gravação**: `INSERT ... ON CONFLICT DO NOTHING` em lotes de 5.000
   linhas. Se a chave já existe no banco, o SQLite pula a linha sem erro
   (CA-10).
3. **Contagem**: `SELECT COUNT(*)` na tabela antes e depois de cada arquivo.
   - inseridas = depois − antes
   - ignoradas = linhas enviadas − inseridas

## Transação e falhas (CA-15)

- Uma conexão, uma transação: `with engine.begin() as conn:`. Qualquer
  exceção desfaz tudo, inclusive o `--reset`.
- `PRAGMA foreign_keys=ON` é ativado na conexão do script, como pede o
  `CLAUDE.md` ("Armadilhas conhecidas").
- Em caso de erro inesperado, o script imprime a mensagem, informa que
  nada foi gravado e sai com código `1`.

## Relatório (CA-16, CA-17)

Impresso no terminal ao final:

```text
Carga concluída em 18,4 s

Tabela                    Lidas    Inseridas  Ignoradas  Descartadas
dim_movies               95.645       95.645          0            0
...
movie_reviews            43.666       43.666          0            0

Correções: 4.801 sinopses com aspas corrigidas (CA-18)

Ocorrências:
  movies_reviews.csv: 2 linhas descartadas: nota fora de 0–10 (linhas 10, 57)
  dim_movies.csv: 1 campo anulado: data_lancamento inválida (linha 88)
```

As ocorrências são agrupadas por arquivo e motivo, com até 10 números de
linha por grupo e "... e mais N" quando houver mais. O número da linha é
o do arquivo, contando o cabeçalho como linha 1.

## Arquivos

| Arquivo                                 | Ação    | Conteúdo                                              |
|-----------------------------------------|---------|-------------------------------------------------------|
| `backend/app/movies/load_data.py`       | Criar   | Script completo: leitura, validação, gravação, relatório e CLI (`argparse`). |
| `backend/tests/test_load_data.py`       | Criar   | Testes com CSVs pequenos gerados em pasta temporária. |
| `backend/app/core/config.py`            | Alterar | Padrão de `database_url` → `moviestars.db` (DEC-10).  |
| `backend/.env.example`                  | Alterar | `DATABASE_URL` → `moviestars.db` (DEC-10).            |
| `backend/alembic.ini`                   | Alterar | `sqlalchemy.url` → `moviestars.db` (DEC-10).          |
| `README.md`                             | Alterar | Passo da carga em "Como executar", opções e status da feature (CA-4). |
| `CLAUDE.md`                             | Alterar | Resolver os TODOs: comando da carga e caminho dos CSVs. |

### Estrutura de `load_data.py`

| Elemento                         | Responsabilidade                                   |
|----------------------------------|----------------------------------------------------|
| `CSV_FILES`                      | Lista da tabela "Arquivos e ordem de carga".       |
| `LoadError`                      | Exceção para interrupções previstas (CA-3, CA-14). |
| `TableStats`, `LoadReport`       | Contadores por tabela e ocorrências agrupadas (dataclasses). |
| `check_files(data_dir)`          | CA-14.                                             |
| `check_tables(conn)`             | CA-3.                                              |
| `reset_tables(conn)`             | CA-11.                                             |
| `convert_value(column, raw)`     | Conversão por tipo (CA-7, CA-13).                  |
| `fix_synopsis_quotes(text)`      | CA-18.                                             |
| `load_file(conn, ...)`           | Lê, valida, grava em lotes e conta um arquivo.     |
| `run_load(database_url, data_dir, reset) -> LoadReport` | Orquestra tudo numa transação; é o que os testes chamam. |
| `format_report(report) -> str`   | Texto do relatório (CA-16, CA-17).                 |
| `main()`                         | Lê os argumentos, chama `run_load`, imprime e define o código de saída. |

## Testes

Cada teste cria um banco SQLite temporário (`tmp_path`) com
`Base.metadata.create_all` e CSVs mínimos, de 2 ou 3 linhas por arquivo.
Os testes nunca tocam no `moviestars.db` (constituição, seção 6).

| Teste                                                     | CAs            |
|-----------------------------------------------------------|----------------|
| Carga completa em banco vazio grava todas as linhas válidas | CA-1, CA-5    |
| Célula vazia vira `NULL`; acentos preservados; nota sem conversão | CA-7, CA-8, CA-9 |
| Segunda execução: nada duplicado, tudo "ignorado"         | CA-10          |
| `--reset` apaga e recarrega                               | CA-11          |
| Linhas inválidas (título vazio, nota 11, tipo "Produtor", filme inexistente) descartadas; demais gravadas | CA-6, CA-12 |
| Data inválida em campo opcional vira `NULL` e a linha fica | CA-13         |
| Arquivo ausente e coluna ausente interrompem sem gravar nada | CA-14       |
| Banco sem tabelas interrompe com a mensagem de migração   | CA-3           |
| Erro forçado no meio da carga desfaz tudo                 | CA-15          |
| `fix_synopsis_quotes` nos três formatos (duas pontas, só a inicial, sem aspas) | CA-18 |
| Relatório contém contadores e ocorrências agrupadas       | CA-16, CA-17   |
| Casos de borda: chave duplicada, nome duplicado, linha com colunas a mais | CA-12 |

Validação manual com os dados reais no `moviestars.db` (CA-5, RNF-1):
rodar a carga, conferir as contagens do relatório com a tabela Q-3 da spec,
anotar o tempo e rodar de novo para confirmar CA-10.

## Decisões

- **DEC-1. Script em `app/movies/load_data.py`, executado com `python -m`.**
  Fica junto do domínio cujos modelos usa, e os testes o importam como
  qualquer módulo de `app`.
  *Descartado:* script solto em `backend/scripts/`, porque os testes
  precisariam ajustar o `sys.path` para importá-lo. *Descartado:* endpoint
  HTTP, que está fora do escopo da spec.
- **DEC-2. SQLAlchemy Core síncrono, com o driver `sqlite3` padrão.**
  O script roda sozinho e não atende requisições simultâneas, então o
  async não traz benefício, só complexidade. Core (`insert(tabela)`) grava
  1,7 milhão de linhas muito mais rápido que criar objetos ORM. O Alembic
  já faz o mesmo (`migrations/env.py` remove o `+aiosqlite` da URL). A API
  continua 100% assíncrona, como pede a constituição.
  *Descartado:* `AsyncSession` + ORM.
- **DEC-3. Colunas e tipos lidos do `models.py`.** O script usa
  `Base.metadata.tables[...]` para saber as colunas esperadas, quais são
  obrigatórias e o tipo de cada uma. Assim o esquema fica definido num
  lugar só.
  *Descartado:* mapeamento escrito à mão por arquivo, que duplicaria o
  esquema e poderia divergir dele.
- **DEC-4. Leitura em fluxo e gravação em lotes de 5.000 linhas.** Cada
  arquivo é lido linha a linha, sem carregar os 233 MB inteiros na memória.
  Na memória ficam só os conjuntos de chaves válidas.
  *Descartado:* ler tudo de uma vez, o que poderia passar de 1 GB de
  memória.
- **DEC-5. "Ignoradas" via `ON CONFLICT DO NOTHING` + contagem antes e
  depois.** Detecta chaves já existentes sem carregar do banco todas as
  chaves das tabelas grandes, como os 745 mil pares de
  `bridge_movie_person`.
  *Descartado:* `INSERT OR IGNORE`, que também engole violações de
  `NOT NULL` e `CHECK` e esconderia erros. *Descartado:* pré-carregar todas
  as chaves, pelo custo de memória.
- **DEC-6. Regras do banco (CHECK, FK, unicidade de nome) verificadas em
  Python antes do insert.** Uma única violação no banco abortaria a
  transação inteira. Verificando antes, a linha é descartada e as demais
  seguem (CA-12).
  *Descartado:* capturar o erro linha a linha, que exigiria inserir uma
  linha por vez (lento) ou usar savepoints (complexo).
- **DEC-7. CA-3 verificado pela existência das 10 tabelas.** É simples e
  cobre o caso real ("esqueci de rodar as migrações").
  *Descartado:* comparar a revisão do Alembic no banco com a mais recente.
  É mais preciso, mas precisa de mais código e de localizar o
  `alembic.ini`.
- **DEC-8. Testes criam o esquema com `Base.metadata.create_all`.** A
  constituição proíbe o `create_all` na aplicação, não nos testes, e ele
  gera o mesmo esquema da migração 0001.
  *Descartado:* rodar as migrações do Alembic nos testes. O `env.py` lê o
  `DATABASE_URL` de configurações em cache (`lru_cache`), o que complica
  apontar para um banco temporário.
- **DEC-9. Nenhuma dependência nova.** Tudo vem da biblioteca padrão
  (`csv`, `argparse`, `decimal`, `datetime`, `time`) ou do que já está no
  `pyproject.toml`.
- **DEC-10. Nome do banco alinhado para `moviestars.db`.** A constituição
  já foi atualizada (seção 8). O padrão em `config.py`, o `.env.example` e
  o `alembic.ini` ainda dizem `rocketlab.db` e passam a dizer
  `moviestars.db`. O `.env` local já usa `moviestars.db` e não é alterado.
- **DEC-11. Relatório com `print` no terminal.** É a saída do comando, não
  um log de diagnóstico.
  *Descartado:* `logging`, que mistura o relatório com mensagens do
  SQLAlchemy. *Descartado:* arquivo de relatório, porque a spec não pede.
- **DEC-12. Estrutura de pastas fixa dentro de `--data-dir`.** O script
  espera as duas subpastas atuais.
  *Descartado:* procurar os arquivos por nome em qualquer subpasta. Seria
  mais flexível, mas ambíguo se houver arquivos com o mesmo nome.

## Riscos

- **RNF-1 (menos de 1 min):** a estimativa é de 10 a 30 s, mas só a
  validação manual confirma. Se passar do limite, o primeiro ajuste é
  aumentar o tamanho do lote.
- **`Decimal` no SQLite:** o SQLAlchemy pode emitir um aviso ao gravar
  `Decimal` em `Numeric` no SQLite. O aviso é inofensivo, porque todos os
  valores têm no máximo 2 casas decimais. Se incomodar, a conversão passa
  a gerar `float`, e isso fica registrado aqui antes de mudar o código.
