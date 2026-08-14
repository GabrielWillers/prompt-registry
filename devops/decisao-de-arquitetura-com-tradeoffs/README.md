---
nome: Decisão de arquitetura com trade-offs
descricao: Compara caminhos alternativos contra restrições duras e brandas antes de recomendar, expondo o que cada opção sacrifica.
versao: 1.0.0
tags: [arquitetura, decisao, tradeoffs, sistemas-distribuidos, sre]
inputs:
  - nome: sistema
    descricao: Sistema ou componente sobre o qual a decisão incide.
  - nome: estado_atual
    descricao: Fatos medidos do sistema hoje (throughput, picos, retenção, consumidores, pontos frágeis).
  - nome: restricoes
    descricao: Restrições que a solução deve respeitar, incluindo SLAs, orçamento e vetos históricos do time.
  - nome: opcoes_candidatas
    descricao: Caminhos já em cima da mesa. Pode vir vazio — o modelo então propõe as opções.
  - nome: contexto_adicional
    descricao: Histórico, stack em uso e restrições organizacionais relevantes. Deixe vazio se não houver.
---

# Decisão de arquitetura com trade-offs

## Objetivo

Impedir que a IA entregue a primeira resposta plausível numa decisão cara de
reverter. O prompt força três coisas que um pedido solto não produz:

1. **Classificar as restrições em duras e brandas.** É o passo de maior
   alavancagem. Sem ele, o modelo trata "não pode perder mensagem" e "orçamento
   estourado" com o mesmo peso. Com ele, a restrição dura **elimina**
   candidatos e a branda apenas os **penaliza** — que é a hierarquia correta.
2. **Comparar no mínimo três opções**, cada uma avaliada contra cada restrição
   dura, com o campo "o que ela NÃO resolve".
3. **Declarar o que a recomendação sacrifica**, por que vence as descartadas, e
   qual é o gatilho de revisão — o que tornaria a recomendação obsoleta.

O prompt é agnóstico de domínio: nasceu de uma decisão de backpressure em
barramento de eventos, mas o método serve a qualquer escolha de arquitetura com
restrições conflitantes.

## Casos de uso

- Escolher entre estratégias concorrentes sob SLA e orçamento apertados.
- Preparar a discussão antes de um ADR: a tabela comparativa e as premissas
  viram o corpo do documento.
- Testar uma decisão que o time já tomou — passe a decisão em
  `opcoes_candidatas` junto com as alternativas e veja se ela sobrevive à
  classificação de restrições.
- Documentar por que uma opção popular foi **descartada**, que é a parte que
  costuma se perder e reaparecer como discussão seis meses depois.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `sistema` | `Relay` (barramento de eventos) |
| `estado_atual` | throughput sustentado 180k msgs/s; pico observado 320k msgs/s por 25min; retenção 4h; consumidores Forge (ingestão) e Sentinel (alerting em tempo real) |
| `restricoes` | alerting do Sentinel não pode atrasar mais que 60s (SLA); ingestão do Forge pode atrasar até 15min; orçamento do trimestre 8% acima do previsto; perda de telemetry é inaceitável |
| `opcoes_candidatas` | prioridade ao Sentinel; dead-letter queue; partição por cliente; auto-scaling de consumidores |
| `contexto_adicional` | vazio |

**Saída (Claude Opus 4.8)** — trechos:

*Problema em uma frase*

> Durante rajadas de um cliente grande, a fila única do Relay faz o alerting em
> tempo real do Sentinel esperar atrás da ingestão em massa do Forge, atrasando
> alertas com SLA de 60s.

*Restrições classificadas*

- **Duras:** não perder telemetry; alerting do Sentinel ≤ 60s.
- **Brandas:** ingestão do Forge pode atrasar até 15min; orçamento 8% acima
  (penaliza, não elimina).
- **Gargalo real:** a assimetria 60s (Sentinel) × 15min (Forge). Na fila
  compartilhada, o volume do Forge starva o caminho de alerta. Os 15min de folga
  são a alavanca.

*Tabela comparativa*

| Opção | Não perde msg? | Protege os 60s? | Custo infra | Risco/complexidade |
|---|---|---|---|---|
| Prioridade ao Sentinel (lanes separadas) | Sim | **Sim, direto** | Baixo | Baixo |
| Partição por cliente (bulkhead) | Sim | Parcial (isola o barulhento; dentro da partição ainda precisa de prioridade) | Médio | Médio |
| Auto-scaling de consumidores | Sim | Parcial — lag de spin-up (rajada de 25min pode acabar antes) | **Alto (fura orçamento)** | Médio |
| Dead-letter queue | Sim (preserva) | **Não** — DLQ é para msg envenenada, não overflow | Baixo | Resolve o problema errado |

*Recomendação* — combinação liderada por prioridade ao Sentinel (lanes
separadas), com partição por cliente no médio prazo e DLQ apenas como rede de
segurança para mensagens não-processáveis. Sacrifica, de propósito, latência de
ingestão do Forge durante rajadas (até os 15min).

*Gatilho de revisão* — se as rajadas virarem carga sustentada acima de 180k/s,
ou se o cliente barulhento passar a ser vários simultâneos, capacidade extra
vira inevitável, orçamento ou não.

**O que a execução demonstrou:** o campo "protege os 60s?" combinado com "o que
ela NÃO resolve" fez o modelo perceber sozinho que a DLQ não reduz latência do
stream vivo. Um prompt ingênuo aceita "guarda o overflow e reprocessa depois"
como resposta boa.

## Limitações conhecidas

- O custo é qualitativo (baixo/médio/alto), não orçado. Para números, o
  `estado_atual` precisa trazer preços e o prompt não valida a conta.
- A recomendação é tão boa quanto as restrições declaradas. Restrição implícita
  que ninguém escreveu não é considerada — e é a causa mais comum de
  recomendação inaplicável.
- O modelo tende a assumir que "barramento de eventos" significa um produto
  específico e importar features dele como dadas. A regra de não assumir
  tecnologia contém isso, mas vale conferir a saída; particularidades de stack
  devem entrar por `contexto_adicional`, nunca ficar implícitas.
- Não substitui prova de carga. A tabela ordena candidatos; o número que
  confirma vem de teste.
