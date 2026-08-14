# Checkpoints — Operação Aegis

Esta pasta **não é uma categoria de prompts**. As categorias do catálogo são as
pastas de domínio na raiz (`devops/`, `desenvolvimento/`, …), conforme o
[`CLAUDE.md`](../CLAUDE.md). Aqui ficam os documentos de entrega do desafio que
deu origem ao playbook: o prompt de cada checkpoint, a execução com modelo e
output, e a curadoria.

A biblioteca em si vive em [`devops/`](../devops/). Estes documentos contam
**como ela foi construída** e por quê.

| # | Checkpoint | Entrega |
|---|---|---|
| 01 | [O primeiro prompt do playbook](./checkpoint-01-o-primeiro-prompt-do-playbook/) | Prompt de triagem de pods + execução nos 3 snapshots |
| 02 | [Padronizando as notas de triagem](./checkpoint-02--padronizando-as-notas-de-triagem/) | Nota de 5 campos + justificativa de método (schema × few-shot) |
| 03 | [Causa-raiz da degradação no Cerebro](./checkpoint-03-causa-raiz-da-degradacao-no-cerebro/) | Análise de causa-raiz cruzando config, métricas e logs |
| 04 | [Segurando a sobrecarga do Relay](./checkpoint-04--segurando-a-sobrecarga-do-relay/) | Decisão de arquitetura com trade-offs |
| 05 | [Migrando o Forge de lote para tempo real](./checkpoint-05-migrando-o-forge-de-lote-para-tempo-real/) | Cadeia de 3 elos, executada ponta a ponta |
| 06 | [Endurecendo a NetworkPolicy do Sentinel](./checkpoint-06-endurecendo-a-networkpolicy-do-sentinel/) | Endurecimento com verificação e refino (v1 → v2 → v3) |
| 07 | [A biblioteca vira código](./checkpoint-07-a-biblioteca-vira-codigo/) | Migração dos prompts para as convenções deste repositório |
| 08 | [Testes determinísticos com promptfoo](./checkpoint-08-testes-deterministicos-com-promptfoo/) | 3 `promptfooconfig.yaml` + execução real dos evals |
| 09 | [Gate de qualidade com LLM-as-judge](./checkpoint-09-gate-de-qualidade-llm-as-judge/) | Rubrica 0–8, juiz calibrado contra pontuação humana |

## Como ler

- **`checkpoint-NN.md`** — o documento da entrega.
- **`saidas-dos-modelos.md`** (CP08 e CP09) — as saídas integrais geradas pelos
  modelos, que é o material que os testes avaliaram.
- **`saida-*.txt`** — o resultado bruto do `promptfoo eval`.
- **`calibracao/`** (CP09) — as 8 fixtures pontuadas à mão e o harness que
  compara juiz e humano.
