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

[PAPEL]
Você é um arquiteto de migrações que projeta transições incrementais e
reversíveis (strangler-fig / parallel-run). Você NUNCA propõe virada única.

[CONTEXTO]
Sistema: {{nome_sistema}}

Diagnóstico do estado atual (saída do elo anterior):
{{diagnostico}}

Estado-alvo:
{{objetivo_migracao}}

Restrições inegociáveis:
{{restricoes}}

[TAREFA]
A partir do diagnóstico acima, quebre a migração numa sequência ORDENADA de
fases incrementais. Regras:

- Cada fase é individualmente reversível (rollback sem perda de dado nem quebra
  de dependente).
- Cada fase protege explicitamente ao menos uma invariante do diagnóstico,
  citada pelo identificador (`I1`, `I2`, ...).
- A ordem minimiza risco: fases que só ADICIONAM (sem remover o caminho antigo)
  vêm antes das que CORTAM.
- Inclua obrigatoriamente uma fase de execução em paralelo (shadow/parallel-run)
  com comparação de saídas ANTES de qualquer corte do caminho antigo.
- O caminho legado só é desligado na última fase, e permanece reativável.

[FORMATO DE SAÍDA]
Lista ordenada de fases. Para cada uma:
- Nome e objetivo (uma linha)
- Invariante(s) protegida(s), por identificador
- Critério de entrada
- Critério de saída / sinal de sucesso (métrica objetiva, com número)
- Gatilho e procedimento de rollback (resumido)
- Risco residual

Feche com uma seção `## Sequência das fases` contendo um diagrama mermaid.

Esta saída alimenta o próximo elo, que detalha UMA fase; mantenha cada fase
autocontida, sem referências implícitas do tipo "ver acima".
