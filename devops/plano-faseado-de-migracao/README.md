---
nome: Plano faseado de migração
descricao: Quebra uma migração em fases incrementais e reversíveis a partir do diagnóstico, com critério de saída e rollback por fase. Elo 2 da cadeia de migração.
versao: 1.0.0
tags: [migracao, arquitetura, planejamento, cadeia-de-prompts, reversibilidade]
inputs:
  - nome: nome_sistema
    descricao: Nome do sistema a migrar (ex. Forge).
  - nome: diagnostico
    descricao: Saída integral do elo 1 (diagnóstico de acoplamento), colada sem edição.
  - nome: objetivo_migracao
    descricao: Estado-alvo desejado após a migração.
  - nome: restricoes
    descricao: Restrições inegociáveis da migração (sem big-bang, reversibilidade, SLAs a preservar).
---

# Plano faseado de migração

> **Elo 2 de 3** da cadeia de migração de arquitetura.
> Elo anterior: [diagnostico-de-acoplamento-para-migracao](../diagnostico-de-acoplamento-para-migracao/).
> Próximo elo: [runbook-de-fase-de-migracao](../runbook-de-fase-de-migracao/).

## Objetivo

Transformar o diagnóstico em uma sequência de passos que possa ser interrompida
a qualquer momento sem deixar o sistema num estado inválido. O prompt embute as
regras que tornam isso possível e que o modelo não aplica sozinho:

- **Aditivo antes de subtrativo.** Fases que só adicionam o caminho novo vêm
  antes das que removem o antigo. É o que garante que existe para onde voltar.
- **Parallel-run obrigatório antes de qualquer corte.** Nenhum plano válido
  desliga o caminho antigo sem antes ter rodado os dois em paralelo comparando
  saídas.
- **Legado desligado só na última fase, e reativável.**
- **Cada fase cita a invariante que protege**, pelo identificador vindo do elo 1.

O `{{diagnostico}}` recebe a saída **integral** do elo 1, colada sem edição. É o
contrato de handoff da cadeia: o elo 1 produz seções nomeadas e invariantes
numeradas justamente para que este elo possa referenciá-las.

## Casos de uso

- Planejar uma migração grande demais para caber num prompt só, depois de rodar
  o elo 1.
- Revisar um plano de migração já escrito por humanos: rode o prompt e compare
  a ordem das fases: virada única disfarçada e ausência de parallel-run são os
  achados mais frequentes.
- Gerar a espinha do épico de migração no board — cada fase vira um item com
  critério de saída objetivo já definido.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `nome_sistema` | `Forge` |
| `diagnostico` | saída integral do elo 1 para o Forge |
| `objetivo_migracao` | consumir do Relay continuamente, processando em pequenos blocos no lugar do lote de 1h |
| `restricoes` | manter dependentes funcionando durante a transição; nada de virada única; cada passo reversível |

**Saída (Claude Opus 5, temperatura `0.2`)** — 6 fases. Uma delas, no molde
completo:

```markdown
### Fase 4 — Parallel-run com comparação automatizada
- **Objetivo:** rodar os dois caminhos e comparar saída contra saída,
  partição a partição.
- **Invariantes protegidas:** I1, I3, I6 — é aqui que a semântica de agregação
  e o tratamento de dado atrasado são provados, não assumidos.
- **Critério de entrada:** fase 3 concluída.
- **Critério de saída:** divergência abaixo de 0,1% em contagem e em soma de
  métrica de billing, em 168 partições horárias consecutivas (7 dias),
  incluindo ao menos um fechamento de mês ou pico conhecido.
- **Rollback:** desligar comparação e consumidor; nenhum dependente foi tocado.
- **Risco residual:** divergência dentro do limiar mas sistemática (viés) pode
  passar. Mitigar comparando distribuição, não só total.
```

A fase 5 (cutover) saiu ordenada por **reversibilidade da falha** — Cerebro →
Sentinel → billing:

> O Cerebro tem a falha mais reversível (reindexar resolve), o Sentinel tem
> impacto operacional mas detectável, e o billing tem a falha mais cara e mais
> silenciosa. O último a migrar é o que menos perdoa.

Essa ordenação vem direto da seção de falhas silenciosas do elo 1 — é o
resultado que mais justifica encadear em vez de usar um prompt único.

```mermaid
flowchart LR
  F1[F1 · Inventário<br/>e baseline] --> F2[F2 · Publicar<br/>no Relay]
  F2 --> F3[F3 · Consumidor<br/>em shadow]
  F3 --> F4[F4 · Parallel-run<br/>+ comparação]
  F4 --> F5[F5 · Cutover<br/>Cerebro→Sentinel→billing]
  F5 --> F6[F6 · Desligar batch<br/>reativável]
```

**Testes estruturais**

- [ ] Saída é lista ordenada de fases.
- [ ] Existe ao menos uma fase de shadow/parallel-run **antes** de qualquer corte.
- [ ] O desligamento do legado é a **última** fase e é reativável.
- [ ] Cada fase cita ao menos uma invariante por identificador do elo 1.
- [ ] Cada fase tem critério de saída com métrica objetiva e gatilho de rollback.
- [ ] Contém `## Sequência das fases` em mermaid.

## Limitações conhecidas

- O plano herda os erros do elo 1. Diagnóstico incompleto gera fases que
  protegem invariantes erradas, e o prompt não tem como perceber.
- Os números dos critérios de saída são plausíveis, não calibrados — o modelo
  não conhece a variância real do sistema. Trate-os como ponto de partida a
  negociar com quem opera.
- Não estima esforço nem duração de fase. É sequenciamento por risco, não
  cronograma.
- Custo de contexto: colar o diagnóstico inteiro incha a entrada. Em sistemas
  grandes, compacte antes, preservando invariantes e riscos priorizados.
