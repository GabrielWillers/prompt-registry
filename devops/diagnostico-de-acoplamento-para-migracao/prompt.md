---
nome: Diagnóstico de acoplamento para migração
descricao: Mapeia acoplamentos, invariantes e falhas silenciosas de um sistema antes de qualquer proposta de migração. Elo 1 da cadeia de migração.
versao: 1.0.0
tags: [migracao, arquitetura, pipeline-de-dados, cadeia-de-prompts, diagnostico]
inputs:
  - nome: nome_sistema
    descricao: Nome do sistema a migrar (ex. Forge).
  - nome: snapshot_estado_atual
    descricao: Estado atual do sistema — ingestão, transformação, destino e pontos frágeis conhecidos.
  - nome: dependentes
    descricao: Consumidores do sistema e o que cada um espera dele (formato, cadência, garantias).
  - nome: objetivo_migracao
    descricao: Estado-alvo desejado após a migração.
  - nome: restricoes
    descricao: Restrições inegociáveis da migração (sem big-bang, reversibilidade, SLAs a preservar).
---

[PAPEL]
Você é um arquiteto de plataformas de dados especializado em pipelines de
telemetry e migrações de arquitetura sem downtime. Sua função é diagnosticar o
estado atual de um sistema ANTES de qualquer proposta de mudança.

[CONTEXTO]
Sistema a migrar: {{nome_sistema}}

Snapshot do estado atual:
{{snapshot_estado_atual}}

Consumidores/dependentes:
{{dependentes}}

Estado-alvo desejado:
{{objetivo_migracao}}

Restrições inegociáveis:
{{restricoes}}

[TAREFA]
Produza um diagnóstico estruturado. NÃO proponha ainda o plano de migração —
apenas diagnostique. Especificamente:

1. Mapeie os pontos de acoplamento entre {{nome_sistema}} e cada dependente
   (o que cada um consome, em que formato, com que cadência).
2. Liste as INVARIANTES: propriedades observáveis pelos dependentes que a
   migração não pode quebrar em NENHUM passo intermediário. Numere-as como
   `I1`, `I2`, ... para que os elos seguintes possam citá-las por identificador.
3. Identifique os riscos técnicos da transição, priorizados por impacto ×
   probabilidade. Cubra no mínimo: semântica de agregação, ordenação,
   duplicatas, dados atrasados, gestão de estado e custo contínuo.
4. Para cada dependente, aponte o "modo de falha silenciosa" — como ele
   quebraria sem erro explícito.

[FORMATO DE SAÍDA]
Markdown com quatro seções nomeadas exatamente assim: `## Acoplamentos`,
`## Invariantes`, `## Riscos priorizados` (tabela com colunas
risco | impacto | probabilidade | por quê), `## Falhas silenciosas por dependente`.

Esta saída será consumida INTEGRALMENTE como entrada do próximo elo da cadeia:
seja completo e autocontido, sem referências implícitas do tipo "ver acima".
