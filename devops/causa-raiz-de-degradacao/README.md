---
nome: Análise de causa-raiz de degradação
descricao: Cruza configuração, métricas e logs de uma janela de incidente para chegar à causa-raiz com cadeia causal ancorada em evidência.
versao: 1.0.0
tags: [sre, incidentes, causa-raiz, observabilidade, diagnostico]
inputs:
  - nome: sistema
    descricao: Sistema sob análise (ex.: Cerebro, Forge, Relay, Sentinel).
  - nome: janela
    descricao: Janela temporal do incidente, com fuso (ex.: 08:00-10:00 UTC 2026-05-13).
  - nome: sintoma_relatado
    descricao: O que o plantão observou antes de escalar, em uma frase.
  - nome: config
    descricao: Arquivo(s) de configuração do sistema vigentes na janela.
  - nome: metricas
    descricao: Série temporal de métricas cobrindo a janela, com uma linha por ponto de coleta.
  - nome: logs
    descricao: Trecho de log da aplicação cobrindo a mesma janela das métricas. Já sanitizado.
  - nome: contexto_adicional
    descricao: Deploys, mudanças de infra ou incidentes correlatos. Deixe vazio se não houver.
---

# Análise de causa-raiz de degradação

## Objetivo

Levar o modelo do sintoma até o **mecanismo**. A degradação de um sistema
distribuído quase sempre se apresenta como vários sintomas simultâneos — latência
alta, cache frio, fila cheia — e a tentação é listar todos e chamar de análise.
Este prompt força a construção de uma cadeia causal `gatilho → mecanismo →
sintomas`, com cada elo ancorado numa linha de log, num ponto de métrica ou num
parâmetro de config.

O que o diferencia de um prompt de diagnóstico genérico:

- exige **correlação entre três artefatos de fontes diferentes** (config,
  métricas, log), não a leitura isolada de cada um;
- exige **hipóteses alternativas descartadas com motivo**, o que impede que a
  primeira explicação plausível vire a conclusão;
- separa **FATO de HIPÓTESE** e obriga a declarar as lacunas de dados, para que
  a confiança da conclusão seja explícita e não implícita.

## Pré-requisito de compliance

O pacote de entrada é telemetria de produção. **A sanitização é upstream, nunca
uma instrução para o modelo** — quando ele recebe o log, o dado sensível já foi
enviado. Antes de preencher `logs` e `metricas`, remova:

- hostnames, IDs de pod e de nó;
- nomes de índice, tópico ou tabela que revelem tenancy de cliente
  (`logs-2026.05` é um exemplo real desse vetor);
- qualquer PII presente em mensagem de log.

Roteamento recomendado: endpoint com retenção zero e sem uso para treino,
temperatura baixa, modelo de raciocínio de fronteira. A escolha do provedor é
decisão de compliance (owner: segurança), não de conveniência.

## Casos de uso

- Degradação progressiva que o plantão não fechou: latência subindo há horas,
  sem erro óbvio e sem deploy correlato.
- Incidente com múltiplos sintomas simultâneos, onde a pergunta real é qual
  deles é a causa e quais são consequência.
- Preparação de postmortem: a cadeia causal e as hipóteses descartadas viram a
  seção de análise do documento.
- Segunda opinião contra a hipótese que o time já tem — o bloco de hipóteses
  alternativas existe justamente para atacar a conclusão precoce.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `sistema` | `Cerebro` |
| `janela` | `08:00–10:00 UTC 2026-05-13` |
| `sintoma_relatado` | `buscas lentas e resultados incompletos` |
| `config` | `cerebro.yaml` — 12 shards, `jvm_heap: 8g`, `refresh_interval: 1s`, job de reindex às 02:00 com duração média de 90min, query cache de 512MB |
| `metricas` | 5 pontos de 30 em 30min: `search_p99_ms` 850→6700, `indexed_docs_per_s` 4200→12400, `heap_used_pct` 61→94, `cache_hit_pct` 74→29 |
| `logs` | log nativo do Elasticsearch de `cerebro-node-3` cobrindo a mesma janela |
| `contexto_adicional` | vazio |

**Resultado de referência (golden)** — a conclusão que uma execução válida
precisa alcançar:

> A reindexação agendada (task 88123, 02:00) não completou na janela off-peak e
> passou a concorrer com a ingestão de pico sobre um heap de 8g subdimensionado
> para carga concorrente (agravado por `refresh_interval: 1s`), levando à
> exaustão de heap que dispara o circuit breaker e cascateia em cache, fila de
> escrita e busca.

**Critérios de aprovação da execução**

1. **Chega na causa-raiz**, não para em sintoma: a exaustão de heap tem origem
   no overrun do reindex concorrente com a ingestão de pico. Apontar "heap
   cheio" ou "circuit breaker disparou" como causa é reprovação — ambos são
   mecanismo e sintoma, não gatilho.
2. **Cita as âncoras corretas**: reindex ainda em 41% às 09:58; circuit breaker
   a 96% e `CircuitBreakingException` às 10:01; e a ordem temporal em que
   `indexed_docs_per_s` sobe **antes** de `search_p99_ms` — é isso que sustenta
   a direção da causa (escrita afoga leitura, não o contrário).
3. **Declara as lacunas**: não há dado sobre o motivo do atraso do reindex entre
   02:00 e 08:00, nem `qps` de busca. A confiança global precisa refletir isso.

> Nota de estado: os critérios acima estão validados como golden set, mas a
> transcrição integral da saída do modelo não foi arquivada nesta versão. Ao
> rodar, salve o output completo junto deste README.

## Limitações conhecidas

- Analisa **um** sistema por execução. Incidente que cruza Relay → Forge →
  Cerebro precisa de uma execução por sistema mais uma síntese manual.
- A qualidade da conclusão é limitada pela janela colada. Se o gatilho está
  fora dela — aqui, o motivo do atraso do reindex entre 02:00 e 08:00 — o
  prompt chega ao mecanismo mas não ao gatilho, e deve dizê-lo.
- Log é amostra de **um nó**. Problema restrito a outro nó ou a um shard não
  amostrado não aparece.
- Pacotes grandes (log de horas em nível DEBUG) diluem a atenção do modelo.
  Recorte para a janela do incidente antes de colar.
- Só é seguro rodar depois da sanitização descrita acima.
