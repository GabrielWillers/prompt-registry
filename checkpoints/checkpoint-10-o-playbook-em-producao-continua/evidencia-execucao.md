# Evidência de execução do pipeline

## 1. Build VERDE — push na main (run 31830080161)
```
success	devops/decisao-de-arquitetura-com-tradeoffs
success	devops/networkpolicy-sentinel
success	devops/nota-de-triagem
success	devops/causa-raiz
success	devops/triagem-de-pods
success	devops/diagnostico-de-acoplamento-para-migracao
success	devops/plano-faseado-de-migracao
success	devops/runbook-de-fase-de-migracao
success	Convenções do catálogo
success	Definir escopo
success	Compatibilidade (informativo)
```

## 2. Build VERMELHO — PR #1 com prompts regredidos (run 31831316149)
```
success	Convenções do catálogo
success	Definir escopo
success	devops/causa-raiz
failure	devops/runbook-de-fase-de-migracao
skipped	Compatibilidade (informativo)
```

### Log do job que barrou
```
│ Forge              │ Fase 4 —           │ 14 etapas em Spark │ ## Invariantes     │ ### Fase 3 —       │ [FAIL] ##          │
✓ Eval complete (ID: eval-Q2i-2026-08-14T19:02:03)
  0 passed (0%)
  ✗ 1 failed (100%)
##[error]Error: Evaluation success rate (0.00%) is below the required threshold (100%)
Help: Consider adjusting your prompts or lowering the threshold
...
# segunda tentativa (retry automático):
│ Forge              │ Fase 4 —           │ 14 etapas em Spark │ ## Invariantes     │ ### Fase 3 —       │ [ERROR] Error: No  │
✓ Eval complete (ID: eval-xL2-2026-08-14T19:02:15)
  0 passed (0%)
  0 failed (0%)
##[error]Error: Evaluation success rate (0.00%) is below the required threshold (100%)
Help: Consider adjusting your prompts or lowering the threshold
```

A tentativa 1 falhou, o retry rodou e falhou também — o build caiu.
Fosse instabilidade de provedor, a segunda teria passado e o build seguiria
verde com um aviso de suíte instável.
