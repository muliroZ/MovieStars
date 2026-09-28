# 102 — Docker e CI

| Campo          | Valor                                                  |
|----------------|--------------------------------------------------------|
| Status         | Concluída (registrada depois da implementação)         |
| Depende de     | 000 (carga dos dados); 101 (cache de consultas, um único processo) |
| Bloqueia       | —                                                      |
| Referências    | `specs/constitution.md` (seções 1, 2, 6, 7)            |

> **Registro retroativo.** O desenvolvedor implementou esta feature
> diretamente, fora do fluxo spec → plan → tasks (commits `6e69130` e
> `c846203`, 2026-09-27). Os três documentos foram escritos depois, a pedido
> dele, para manter o histórico completo. Eles descrevem o que existe e as
> verificações que foram feitas.

## Contexto

Para rodar a aplicação hoje, é preciso instalar o Python e o Bun, criar o
ambiente do backend, aplicar as migrações, carregar os CSVs e subir a API e o
frontend em dois terminais. Quem só quer ver a aplicação funcionando, como um
avaliador da atividade, precisa seguir todos esses passos.

Além disso, as verificações da definição de pronto (constituição, seção 6)
rodam só na máquina de quem desenvolve. Nada impede que uma mudança quebre
os testes, o lint ou o build e chegue à `main` assim mesmo.

Esta feature acrescenta duas coisas:
- um jeito de subir a aplicação inteira com um comando, sem instalar nada
  além do Docker;
- uma verificação automática, no repositório, de cada mudança enviada.

## Histórias de usuário

- **H-1.** Como avaliador ou desenvolvedor, quero subir a aplicação inteira
  com um comando, já com o catálogo carregado, sem instalar Python nem Bun.
- **H-2.** Como desenvolvedor, quero atualizar o repositório e subir de novo
  sem refazer a carga, com as migrações novas aplicadas sozinhas.
- **H-3.** Como desenvolvedor, quero que cada mudança enviada ao repositório
  seja conferida automaticamente (testes, lint, formatação, migrações, build
  e imagens), para que nada quebrado chegue à `main`.

## Critérios de aceitação

### Aplicação em containers

- **CA-1** (H-1). Um único comando, na raiz do projeto, constrói e sobe a
  API e o frontend. A aplicação fica em `http://localhost:8080`, a API em
  `http://localhost:8000/api/v1` e a documentação da API em
  `http://localhost:8000/docs`.
- **CA-2** (H-1). Na primeira subida, a API aplica as migrações e carrega os
  CSVs de `data/` antes de responder. O catálogo aparece completo (95.645
  filmes) sem nenhum passo manual.
- **CA-3** (H-2). Nas subidas seguintes, a carga não é refeita e os dados
  criados pela aplicação continuam lá. As migrações novas são aplicadas a
  cada subida.
- **CA-4** (H-1). O frontend dos containers funciona como o local: catálogo,
  busca, filtros, detalhes, formulários e avaliações falam com a API sem erro
  de conexão.
- **CA-5** (H-1). Recarregar a página em qualquer rota do frontend (ex.:
  `/filmes/<id>`) abre a tela certa, e não um erro de página inexistente.
- **CA-6** (H-1). O banco dos containers é separado do banco do
  desenvolvimento local: um não altera o outro.
- **CA-7**. A API dos containers roda como um único processo, como exige o
  cache de consultas (spec 101, D-9).
- **CA-8**. Os CSVs de `data/` ficam disponíveis para os containers só para
  leitura.

### Verificação automática

- **CA-9** (H-3). Cada push na `main` e cada pull request disparam a
  verificação automática.
- **CA-10** (H-3). No backend, a verificação roda o lint, confere a
  formatação, roda os testes, aplica as migrações num banco vazio e confere
  que modelos e migrações estão em sincronia.
- **CA-11** (H-3). O backend é verificado em todas as versões de Python que o
  projeto suporta, da mínima (3.11) à mais nova (3.14).
- **CA-12** (H-3). No frontend, a verificação instala as dependências
  exatamente nas versões registradas, roda o lint e gera o build (que confere
  os tipos).
- **CA-13** (H-3). As imagens dos containers só são construídas depois que o
  backend e o frontend passam, e a construção também é verificada.
- **CA-14**. Um envio novo para o mesmo branch cancela a verificação anterior
  que ainda estiver rodando.
- **CA-15**. A verificação só lê o repositório; ela não tem permissão para
  alterá-lo.
- **CA-16**. A verificação nunca usa o banco de desenvolvimento nem arquivos
  de configuração locais.

### Documentação

- **CA-17**. O README explica como subir e parar os containers, o que esperar
  da primeira subida, os endereços, a separação dos bancos e como conferir
  localmente o que a verificação automática confere.

## Casos de borda

| Situação                                                        | Comportamento esperado                                   |
|-----------------------------------------------------------------|----------------------------------------------------------|
| Portas 8000 ou 8080 ocupadas (ex.: API ou frontend locais no ar) | Os containers não sobem; o README pede para liberar as portas. |
| Apagar o banco dos containers                                   | A próxima subida refaz a carga dos CSVs (CA-2).          |
| Recarregar os dados com os containers no ar                     | Há um comando documentado; depois, reiniciar a API esvazia o cache. |
| Frontend local (porta 5173) apontando para a API dos containers | Bloqueado pelo navegador (a API dos containers só aceita a origem da porta 8080). |
| Modelo alterado sem a migração correspondente                   | A verificação automática falha (CA-10).                  |
| Código com sintaxe que só existe em versões novas do Python     | A verificação falha na versão 3.11 (CA-11).              |

## Consequências conhecidas

- **Dois bancos.** Filmes e avaliações criados nos containers não aparecem
  no desenvolvimento local, e vice-versa (CA-6).
- **Endereço da API fixo no frontend dos containers.** O frontend chama a API
  em `http://localhost:8000`, pela porta publicada; outro endereço exige
  gerar o frontend de novo.
- **Versões das dependências do backend.** Cada construção da imagem e cada
  verificação instalam as versões mais recentes permitidas, que podem diferir
  das do ambiente local (não há arquivo de versões travadas no backend).

## Decisões

Tomadas pelo desenvolvedor na implementação; os detalhes técnicos estão no
plan.

- **D-1.** Dois serviços, API e frontend, sem um serviço de banco: o banco é
  um arquivo, guardado num volume que sobrevive à recriação dos containers.
- **D-2.** A primeira subida carrega os dados sozinha, e as seguintes só
  aplicam as migrações.
- **D-3.** O frontend dos containers é o de produção (arquivos gerados e
  servidos por um servidor web), não o servidor de desenvolvimento.
- **D-4.** A verificação automática roda no próprio repositório (GitHub), com
  três etapas: backend, frontend e imagens, nessa dependência.
- **D-5.** O backend é verificado em várias versões de Python ao mesmo tempo.

## Fora de escopo

- Publicar as imagens num registro ou fazer deploy automático.
- Servidor de desenvolvimento com recarga automática dentro dos containers.
- Banco de dados fora de arquivo (ex.: PostgreSQL).
- HTTPS, domínio próprio ou proxy reverso único para API e frontend.
- Travar as versões das dependências do backend.
- Testes de frontend ou de ponta a ponta na verificação automática (os
  roteiros de navegador continuam manuais).
