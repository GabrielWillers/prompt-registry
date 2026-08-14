# Catálogo de prompts

> **Entrega do desafio Operação Aegis.** Este repositório é a biblioteca de
> prompts do playbook de IA operacional da Aegis, construída ao longo dos
> Checkpoints 01 a 09.
>
> - **A biblioteca** — 8 prompts parametrizáveis em [`devops/`](./devops/), cada
>   um com `prompt.md`, `README.md` e, quando a saída é verificável,
>   `promptfooconfig.yaml`.
> - **As entregas dos checkpoints** — prompt, execução com modelo e output, e
>   curadoria de cada um, em [`checkpoints/`](./checkpoints/).
> - **Testes** — os 8 prompts têm suíte executável, e o pipeline em
>   [GitHub Actions](./.github/workflows/playbook.yml) roda a cada PR e push,
>   barrando regressão. Veja [como rodar](#rodando-os-testes).


Coleção de prompts em Markdown organizados por categoria/área de domínio. Cada prompt vive em sua própria pasta, contendo o arquivo `prompt.md` (texto puro, pronto para copiar e colar) e um `README.md` com metadados, variáveis e exemplos de uso.

Este repositório faz parte do material dos projetos da pós-graduação em AIOps e Inteligência Artificial com Engenharia Cloud: [pos.veronez.io/pos-aiops](https://pos.veronez.io/pos-aiops/).

Convenções de estrutura, nomenclatura e manutenção estão em [`CLAUDE.md`](./CLAUDE.md).

## Como usar

1. Navegar até a categoria de interesse.
2. Abrir o `README.md` do prompt para entender objetivo, variáveis esperadas e limitações.
3. Copiar o conteúdo do `prompt.md` e substituir os placeholders `{{nome_variavel}}` pelos valores desejados.

## Adicionando um prompt

Use o slash command [`/catalogar`](./.claude/commands/catalogar.md) passando o texto do prompt como argumento. Ele analisa, propõe organização (categoria, slug, frontmatter) e, após sua aprovação, escreve os arquivos e atualiza os índices — sem commitar. Convenções completas em [`CLAUDE.md`](./CLAUDE.md).

## Categorias

### [Desenvolvimento](./desenvolvimento/)

Escrita, revisão e refatoração de código, design de APIs e arquitetura, debugging, testes e documentação técnica.

_Nenhum prompt cadastrado ainda._

### [DevOps](./devops/)

Pipelines de CI/CD, containers, orquestração, infraestrutura como código, observabilidade, SRE e segurança operacional.

Abriga o **playbook de IA operacional da Aegis** — 8 prompts de plantão, diagnóstico, decisão de arquitetura, migração e segurança:

- [triagem-de-pods](./devops/triagem-de-pods/) — transforma um snapshot estático de um namespace Kubernetes em triagem com causa provável por pod e próxima ação do plantão.
- [nota-de-triagem](./devops/nota-de-triagem/) — converte um alerta bruto de monitoramento na nota de triagem padronizada de cinco campos usada na passagem de turno.
- [causa-raiz](./devops/causa-raiz/) — cruza configuração, métricas e logs de uma janela de incidente para chegar à causa-raiz com cadeia causal ancorada em evidência.
- [decisao-de-arquitetura-com-tradeoffs](./devops/decisao-de-arquitetura-com-tradeoffs/) — compara caminhos alternativos contra restrições duras e brandas antes de recomendar, expondo o que cada opção sacrifica.
- [diagnostico-de-acoplamento-para-migracao](./devops/diagnostico-de-acoplamento-para-migracao/) — mapeia acoplamentos, invariantes e falhas silenciosas de um sistema antes de qualquer proposta de migração _(elo 1 de 3)_.
- [plano-faseado-de-migracao](./devops/plano-faseado-de-migracao/) — quebra uma migração em fases incrementais e reversíveis a partir do diagnóstico, com critério de saída e rollback por fase _(elo 2 de 3)_.
- [runbook-de-fase-de-migracao](./devops/runbook-de-fase-de-migracao/) — detalha uma fase do plano como runbook executável, com portões de validação e rollback com critério objetivo de abort _(elo 3 de 3)_.
- [networkpolicy-sentinel](./devops/networkpolicy-sentinel/) — converte um manifesto de NetworkPolicy permissivo em política default-deny mínima, com regras comentadas e autoverificação de segurança.

### [Produtividade](./produtividade/)

Organização pessoal, gestão de tempo e tarefas, rotina, hábitos, foco e decisões sobre fluxo de trabalho individual.

_Nenhum prompt cadastrado ainda._

### [Finanças](./financas/)

Orçamento, investimentos, planejamento financeiro, impostos e apoio a decisões financeiras.

_Nenhum prompt cadastrado ainda._

### [Criação de Conteúdo](./criacao-conteudo/)

Roteiros, artigos, posts para redes sociais, material didático e copy de divulgação.

_Nenhum prompt cadastrado ainda._

<!--
Ao adicionar um prompt, substituir "Nenhum prompt cadastrado ainda" pela lista:

- [nome-do-prompt](./<slug-da-categoria>/<slug-do-prompt>/) — o que o prompt faz, em uma linha.
-->

## Checkpoints do desafio

A pasta [`checkpoints/`](./checkpoints/) **não é uma categoria de prompts** — as
categorias são as pastas de domínio acima. Ela guarda os documentos de entrega do
desafio que originou este playbook: para cada checkpoint, o prompt, a execução
com modelo e output, e a curadoria. É o registro de **como** a biblioteca foi
construída; a biblioteca em si está em [`devops/`](./devops/).

## Rodando os testes

Requer **Node ≥ 22.22** e chaves dos dois providers:

```bash
export OPENAI_API_KEY=...   # openai:gpt-4o-mini (e o juiz gpt-4o no CP09)
export GOOGLE_API_KEY=...   # google:gemini-3.1-flash-lite

cd devops/nota-de-triagem
npx promptfoo@0.122.0 eval -c promptfooconfig.yaml --no-cache -j 2 --delay 2000
```

O `-j 2 --delay 2000` existe por causa do limite de 20 req/min do free tier do
Gemini; com conta paga, rode sem eles.

Prompts com suíte: [`nota-de-triagem`](./devops/nota-de-triagem/),
[`triagem-de-pods`](./devops/triagem-de-pods/),
[`networkpolicy-sentinel`](./devops/networkpolicy-sentinel/) e
[`causa-raiz`](./devops/causa-raiz/) — este último com gate por LLM-as-judge.

## Contribuindo

Antes de adicionar ou alterar um prompt, revisar [`CLAUDE.md`](./CLAUDE.md) — a seção **Manutenção da documentação** lista todos os arquivos que precisam ser atualizados junto com a mudança (este índice incluso).
