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

**Configuração de execução:** Claude Opus 4.8, temperatura `0.2`.

**Forma da saída esperada**:

```markdown
## Pré-checagens
1. Confirmar que o lote batch da hora anterior fechou sem erro.
2. Confirmar retenção do Relay suficiente para reprocessar a janela de teste.

## Execução
1. Implantar o consumidor shadow com escrita direcionada a tabelas `_shadow`.
   **Resultado esperado:** consumer group ativo, lag decrescente.
2. ...

## Portões de validação
- Após o passo 1 — **I1**: a partição horária de produção permanece intocada.
  Consulta de contagem por partição antes/depois deve dar diferença zero.

## Rollback
**Critério de abort: divergência acima de 1% em qualquer partição, ou lag do
consumer shadow acima de 15min por mais de 10min seguidos.**
1. Escalar o consumidor shadow para zero réplicas.
2. ...

## Definition of Done
- 7 partições consecutivas com divergência abaixo de 0,1%.
```

> Nota de estado: a saída integral desta execução não foi arquivada nesta
> versão. Ao rodar a cadeia, salve o output dos três elos como golden.

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
