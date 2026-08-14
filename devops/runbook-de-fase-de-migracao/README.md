---
nome: Runbook de fase de migração
descricao: Detalha uma fase do plano como runbook executável, com portões de validação e rollback com critério objetivo de abort. Elo 3 da cadeia de migração.
versao: 1.0.0
tags: [migracao, runbook, sre, cadeia-de-prompts, rollback]
inputs:
  - nome: nome_sistema
    descricao: Nome do sistema a migrar (ex.: Forge).
  - nome: plano_faseado
    descricao: Saída integral do elo 2 (plano faseado), colada sem edição.
  - nome: diagnostico
    descricao: Saída integral do elo 1, usada como referência de invariantes e falhas silenciosas.
  - nome: fase_alvo
    descricao: Qual fase do plano detalhar como runbook nesta execução. Exatamente uma.
  - nome: contexto_tecnico
    descricao: Stack, ferramentas, acessos e restrições operacionais do ambiente onde a fase será executada.
---

# Runbook de fase de migração

> **Elo 3 de 3** da cadeia de migração de arquitetura.
> Elo anterior: [plano-faseado-de-migracao](../plano-faseado-de-migracao/).

## Objetivo

Converter **uma** fase do plano em runbook que o plantonista executa às 3h da
manhã sem precisar interpretar nada. Duas instruções carregam o peso:

- **`CRITÉRIO OBJETIVO DE ABORTAR`.** Por default o modelo escreve rollback
  vago — "se der problema, reverter". A exigência de um número ou condição
  verificável é o que transforma o rollback em procedimento e não em intenção.
- **Uma fase por execução.** Sem isso o modelo detalha todas as fases de forma
  rasa, que é o oposto do que a cadeia existe para evitar. Para cobrir o plano
  inteiro, rode o elo uma vez por fase, variando `fase_alvo`.

Recebe tanto o plano (elo 2) quanto o diagnóstico (elo 1): o plano diz o que
fazer, o diagnóstico diz o que não pode quebrar enquanto se faz.

## Casos de uso

- Preparar a execução da próxima fase de uma migração em andamento.
- Gerar o runbook que acompanha a change request / janela de manutenção.
- Forçar a explicitação do critério de abort antes da janela, quando ainda dá
  para discutir o número com calma.
- Ensaiar o rollback: a regra "o rollback é testado antes de ser necessário"
  produz o passo de validação do caminho de volta.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `nome_sistema` | `Forge` |
| `plano_faseado` | saída integral do elo 2 |
| `diagnostico` | saída integral do elo 1 |
| `fase_alvo` | `Fase 3 — Parallel-run do consumidor de eventos` |
| `contexto_tecnico` | Spark no pipeline atual; consumo do Relay; warehouse particionado por hora; deploy via GitOps |

**Saída (Claude Opus 5, temperatura `0.2`)** — 7 passos de execução, 6 portões
de validação. Extratos:

*Pré-checagens*

> 3. Confirmar que as tabelas `*_shadow` estão isoladas — nenhuma grant de
>    leitura para os papéis do Sentinel, do Cerebro ou do billing. É o que
>    protege **I3** durante toda a fase.

*Execução* (passo 3, o mais específico)

> **Comparar em três níveis, não só no total:** contagem de eventos, soma da
> métrica de billing e **distribuição por chave** (percentis por tenant).
> *Por que os três:* total igual com distribuição diferente é o caso que passa
> no teste e quebra a fatura de um cliente específico.

*Portões de validação*

| Após o passo | Invariante | Como verificar |
|---|---|---|
| 2 | **I3** | Contagem por partição no shadow contra o baseline da fase 1 |
| 4 | **I2** | Reexecutar a comparação de uma partição já comparada 24h antes: resultado idêntico. Diferença significa que uma partição fechada mudou |
| 6 | **I6** | O evento atrasado caiu na partição da hora do evento nos dois caminhos |

*Rollback*

> **Critério de abort: divergência de contagem ou de soma de billing acima de 1%
> em qualquer partição isolada, OU acima de 0,1% em 3 partições consecutivas, OU
> qualquer divergência na verificação de dado atrasado, OU lag do consumidor
> acima de 15min por mais de 10min seguidos.**
>
> O critério é assimétrico de propósito: 1% pontual pode ser um evento isolado,
> mas 0,1% que se repete três vezes seguidas é viés sistemático — e viés é pior
> que ruído, porque não se corrige sozinho.
>
> *Ensaio do rollback:* executar os passos 1 a 4 uma vez, deliberadamente, no
> terceiro dia da fase. Um rollback que nunca foi executado é uma hipótese, não
> um procedimento.

**Testes estruturais**

- [ ] Saída contém `## Pré-checagens`, `## Execução`, `## Portões de validação`,
      `## Rollback`, `## Definition of Done`.
- [ ] `## Execução` é numerada.
- [ ] `## Rollback` contém um número ou condição objetiva de abort, não texto vago.
- [ ] Portões de validação referenciam invariante(s) por identificador.
- [ ] Detalha exatamente **uma** fase (a de `fase_alvo`), não várias.

## Limitações conhecidas

- Comandos concretos dependem inteiramente de `contexto_tecnico`. Se ele for
  vago, o runbook sai com blocos marcados como PENDÊNCIA — o que é o
  comportamento correto, mas exige preenchimento humano antes de executar.
- O critério de abort é uma proposta baseada no plano, não um limiar medido.
  Precisa ser validado contra a variância real antes da janela.
- O runbook não foi executado em ambiente real por este prompt. Ensaio em
  staging continua obrigatório.
- Cobre uma fase; a cadeia inteira exige uma execução por fase, e a consistência
  entre runbooks de fases diferentes é responsabilidade de quem revisa.
