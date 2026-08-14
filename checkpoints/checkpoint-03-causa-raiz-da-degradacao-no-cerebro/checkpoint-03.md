---
id: rca-degradacao
titulo: Análise de causa-raiz de degradação
versao: 1.0.0
status: ativo
owner: SRE — Sam Wilson
criado: 2026-05-13
categoria: incident-response
parametros:
  - SISTEMA              # sistema sob análise (ex.: Cerebro, Forge, Relay, Sentinel)
  - JANELA               # janela temporal do incidente (ex.: 08:00–10:00 UTC 2026-05-13)
  - SINTOMA_RELATADO     # o que o plantão observou antes de escalar
  - CONFIG               # arquivo(s) de configuração do sistema
  - METRICAS             # série temporal de métricas na janela
  - LOGS                 # trecho de log cobrindo a mesma janela
  - CONTEXTO_ADICIONAL   # opcional; deixe vazio se não houver
roteamento:
  provedor: endpoint com zero-retention / sem treino  # obrigatório p/ dados de produção
  temperatura: baixa
  modelo: modelo de raciocínio de fronteira
pre_processamento:
  - "REDAÇÃO UPSTREAM obrigatória antes de preencher {{LOGS}}/{{METRICAS}}:
     remover hostnames, IDs de pod/nó, nomes de índice que revelem tenancy de
     cliente e qualquer PII. O prompt assume entrada já sanitizada."
changelog:
  - 1.0.0 — versão inicial. Validada no pacote de artefatos do Cerebro.
---

# rca-degradacao — Análise de causa-raiz de degradação

Construído por meta-prompting em três rodadas. A primeira gerou um analisador de
incidentes genérico, que parou no sintoma: listou heap alto, cache frio e fila
cheia lado a lado, sem dizer qual causava qual. A segunda rodada foi a que
importou — pedi à IA que criticasse o próprio prompt procurando onde ele
permitiria confundir correlação com causa, e dela saíram o passo de ordenação
temporal e a exigência de descartar hipóteses alternativas com motivo. A terceira
fechou o contrato de saída em nove seções fixas.

## PROMPT

```
## Papel e objetivo
Você é um analista de confiabilidade (SRE) sênior, especialista em diagnóstico
de incidentes em sistemas distribuídos. Recebe um pacote de telemetria de UM
sistema da plataforma e precisa chegar à CAUSA-RAIZ da degradação — o mecanismo
que origina o problema —, não à lista de sintomas. Sintoma listado sem cadeia
causal é resposta incompleta.

## Entrada (parâmetros)
Sistema sob análise : {{SISTEMA}}
Janela do incidente : {{JANELA}}
Sintoma relatado    : {{SINTOMA_RELATADO}}

<config>
{{CONFIG}}
</config>

<metricas>
{{METRICAS}}
</metricas>

<logs>
{{LOGS}}
</logs>

<contexto_adicional>
{{CONTEXTO_ADICIONAL}}
</contexto_adicional>

## Como raciocinar (siga a ordem e mostre o trabalho)
1. Reconstrua UMA linha do tempo cruzando os três artefatos: alinhe cada ponto
   de métrica com as linhas de log do mesmo horário e com os limites da config.
2. Separe as camadas: (a) sintomas observáveis, (b) mecanismo proximal,
   (c) gatilho de origem. Pergunte de cada sintoma "o que causou isto?" até
   chegar num elo que a config/dados expliquem e que não seja causado por outro.
3. Monte a cadeia causal explícita: gatilho → mecanismo → sintomas em cascata.
4. Ancore CADA elo numa evidência: cite a linha de log (horário) ou o ponto de
   métrica ou o parâmetro de config que o sustenta. Elo sem âncora é hipótese.
5. Teste ao menos duas hipóteses alternativas e diga por que os dados as
   descartam (ex.: ordem temporal, qual métrica se move primeiro).
6. Aponte o que os dados NÃO mostram e que seria necessário pra fechar 100%.

## Regras
- Não invente fatos fora dos artefatos. Se algo não está nos dados, diga.
- Toda afirmação factual referencia o artefato (linha/horário/parâmetro).
- Marque explicitamente FATO vs. HIPÓTESE.
- Se a entrada for insuficiente pra concluir, diga o que falta em vez de chutar.
- Correlação temporal não é causalidade: quando duas séries se movem juntas,
  diga qual se move primeiro e por que isso sustenta a direção da causa.

## Saída (nesta estrutura)
1. Bottom line (2–3 frases): causa-raiz em uma frase + nível de confiança.
2. Linha do tempo correlacionada (métrica ↔ log ↔ config).
3. Cadeia causal: gatilho → mecanismo → sintomas.
4. Causa-raiz: afirmação única e acionável.
5. Sintomas que NÃO são a causa (e por quê).
6. Hipóteses alternativas descartadas + motivo.
7. Ação: contenção imediata × correção definitiva.
8. Lacunas de dados.
9. Confiança global (alta/média/baixa) + o que a aumentaria.
```

---

## Execução

**Modelo:** Claude Opus 5, temperatura 0.2.

**Por que este modelo.** É a tarefa mais difícil da biblioteca: correlacionar
três artefatos de fontes diferentes, ordenar eventos no tempo e distinguir causa
de consequência. Modelo mais fraco lista sintomas — foi exatamente o que o
`gpt-4o-mini` fez quando o gate do CP09 rodou sobre este mesmo pacote, tirando
5/8 e parando no heap esgotado. Temperatura 0.2 porque uma análise de incidente
precisa ser reprodutível: dois SREs rodando o mesmo pacote têm de chegar à mesma
conclusão. **Privacidade é o critério que domina aqui** — log de produção tem
hostname, ID de nó e nome de índice que revela tenancy. Por isso o `roteamento`
no frontmatter exige endpoint com retenção zero e sem treino, e a sanitização é
upstream (ver curadoria).

**Parâmetros:**

- `SISTEMA` = Cerebro
- `JANELA` = 08:00–10:00 UTC 2026-05-13
- `SINTOMA_RELATADO` = buscas lentas e, em alguns casos, resultados incompletos
- `CONFIG` = `cerebro.yaml` (Artefato 1)
- `METRICAS` = série de 5 pontos de 30 em 30min (Artefato 2)
- `LOGS` = log do Elasticsearch de `cerebro-node-3` (Artefato 3)
- `CONTEXTO_ADICIONAL` = vazio

### Output

**1. Bottom line**

A reindexação agendada para as 02:00 não terminou na janela off-peak e ainda
rodava às 10:00, sobrepondo sua carga de escrita à rampa de ingestão do horário
comercial. Os dois fluxos juntos esgotaram o heap de 8g, o circuit breaker de
memória disparou e a busca degradou por consequência. Confiança alta no
mecanismo, média na origem do atraso da reindexação — os dados não cobrem o
intervalo em que ela ficou para trás.

**2. Linha do tempo correlacionada**

| Horário | Métrica | Log | Config relevante |
|---|---|---|---|
| 08:00 | p99 850ms · 4.2k docs/s · heap 61% · cache 74% | — | baseline; `jvm_heap: 8g` |
| 08:02 | — | reindex 88123 em 38% (3.8M/10M) | agendado 02:00, `avg_duration_min: 90` → devia ter fechado ~03:30 |
| 08:14 | — | GC young 620ms, heap 4.9→3.1gb | ainda coleta bem |
| 08:30 | p99 1100ms · 4.1k docs/s · heap 68% · cache 71% | — | |
| 08:41 | — | `IndexingMemoryController` throttla shard [logs-2026.05][7]: "segment writing can't keep up" | `refresh_interval: 1s` × 12 shards |
| 09:00 | p99 2300ms · **9.8k docs/s** · heap 79% · cache 58% | — | ingestão salta 2,4× |
| 09:03 | — | write thread pool 150/200 | |
| 09:12 | — | GC **old** 1.1s, heap 6.3→5.9gb | coleta já não devolve memória |
| 09:20 | — | reindex 88123 em 40% (4.0M/10M) | 2% em 78min |
| 09:30 | p99 4100ms · 11.2k docs/s · heap 88% · cache 41% | — | |
| 09:31 | — | circuit breaker `[parent]` em 6.9gb/8gb (86%), "approaching limit" | |
| 09:44 | — | primeira slow query: shard 7, 2380ms | |
| 09:51 | — | write pool 188/200 | |
| 09:58:41 | — | write pool **cheio** 200/200, rejeitando bulk (`EsRejectedExecutionException`) | |
| 09:58:43 | — | GC old 1.8s, heap 7.6→7.4gb | GC não recupera mais |
| 09:58:44 | — | reindex 88123 **ainda em 41%**, ETA unknown | 8h após o agendamento |
| 09:58:46 | — | query 5031ms estoura timeout de 5000ms → **resultado parcial 11/12 shards** → circuit breaker **dispara** em 7.7gb/8gb (96%) | |
| 09:58:47 | — | eviction do query cache disparando, hit_ratio 0.29 | `query_cache.size_mb: 512` |
| 10:00 | p99 **6700ms** · 12.4k docs/s · heap 94% · cache 29% | — | cache 29% = o 0.29 do log |
| 10:01 | — | `CircuitBreakingException: Data too large, would be [7.9gb/8gb]` | |
| 10:03 | — | 1284 bulks rejeitados nos últimos 5min | |
| 10:05 | — | "all shards failed" em 3 das últimas 20 queries | |

**3. Cadeia causal**

```
GATILHO
  reindex 88123 (agendada 02:00, duração média 90min) não fecha na janela
  off-peak e continua rodando no horário comercial
  [FATO — 08:02 em 38%; 09:58 em 41%, ETA unknown]
        ↓
MECANISMO PROXIMAL
  carga de escrita da reindexação + rampa de ingestão (4.2k → 12.4k docs/s)
  competem pelo mesmo heap e pelo mesmo write thread pool, com refresh_interval
  de 1s multiplicando criação de segmento em 12 shards
  [FATO — métricas 09:00–10:00; 08:41 throttle de segment writing]
        ↓
  heap sobe 61% → 94%; GC passa de young 620ms para old 1.8s sem devolver
  memória; circuit breaker [parent] cruza 86% e dispara em 96%
  [FATO — 08:14, 09:12, 09:31, 09:58:43, 09:58:46]
        ↓
SINTOMAS EM CASCATA
  ├─ query cache é despejado sob pressão de heap: hit 74% → 29%
  │  → cada busca reprocessa mais → p99 850ms → 6700ms
  ├─ write pool satura (150 → 188 → 200/200) → 1284 bulks rejeitados
  └─ buscas estouram o timeout de 5s → resultado parcial (11/12 shards)
     → CircuitBreakingException → "all shards failed" em 3 de 20 queries
```

**4. Causa-raiz**

A reindexação `88123` excedeu em mais de 6 horas sua janela off-peak e passou a
concorrer com a ingestão de pico sobre um heap de 8g que não comporta as duas
cargas simultâneas. Não há guarda-corpo que aborte ou limite a reindexação
quando ela invade o horário comercial — é essa ausência, e não o volume de
busca, que origina a degradação.

**5. Sintomas que NÃO são a causa**

- **Heap em 94%** — mecanismo, não gatilho. Às 08:00 o mesmo heap de 8g
  sustentava 4.2k docs/s com p99 de 850ms. Ele só vira problema sob carga
  concorrente.
- **Cache hit em 29%** — consequência. O cache é despejado *porque* o heap está
  sob pressão; ele não causa a pressão. A queda de 74% para 29% acompanha a
  subida do heap, sempre atrás dela.
- **Circuit breaker disparado** — proteção funcionando como projetado. Ele é o
  sintoma mais visível e o menos informativo sobre a origem.
- **Slow query no shard 7** — o shard 7 é onde o sintoma aparece primeiro
  (é o que está sendo throttled desde 08:41), não onde o problema nasce.
- **Resultado parcial 11/12 shards** — o sintoma que o plantão relatou. Último
  elo da cadeia.

**6. Hipóteses alternativas descartadas**

| Hipótese | Por que os dados a descartam |
|---|---|
| Pico de volume de **busca** saturou o cluster | Ordem temporal. O throttle de indexação aparece às 08:41; a primeira slow query, só às 09:44 — uma hora depois. E quem satura é o **write** thread pool, não o de search. Se a demanda de leitura fosse o motor, a fila de escrita não teria motivo para encher. [Ressalva: sem `qps` de busca nos artefatos, o descarte se apoia em ordenação e em qual pool satura, não em medição direta.] |
| Shard 7 defeituoso / hot spot | O circuit breaker é `[parent]`, isto é, do nó inteiro, e o resultado parcial atinge 11 de 12 shards. Um shard doente não leva o heap do nó a 96%. O shard 7 é o primeiro a sofrer porque é o alvo do throttle de indexação. |
| Heap de 8g simplesmente subdimensionado | Às 08:00, com 4.2k docs/s, o heap estava em 61% e o p99 em 850ms — operação normal. O dimensionamento é **condição contribuinte** sob carga dupla, não o gatilho. Trocar só o heap adia o problema até a próxima reindexação atrasada. |
| Query cache de 512MB pequeno demais | A queda do hit ratio começa depois da subida do heap e é explicada por eviction sob pressão (log de 09:58:47). Aumentar o cache sob heap esgotado piora a pressão de memória. |

**7. Ação**

*Contenção imediata (minutos):*
1. Pausar ou cancelar a task de reindex `88123`. É o único item que remove carga
   sem tocar em tráfego de cliente.
2. Subir `refresh_interval` de `1s` para `30s` temporariamente — corta a criação
   de segmentos e alivia a pressão de merge e de heap durante o pico.
3. Acompanhar `heap_used_pct` e `cache_hit_pct`: a recuperação do hit ratio é o
   sinal de que o heap voltou a ter folga.

*Correção definitiva:*
1. **Deadline com abort na reindexação.** Se não fechou até um horário de corte
   off-peak, aborta e reagenda. É o guarda-corpo que faltava e é o que ataca a
   causa-raiz.
2. **Alerta de progresso do reindex contra a duração esperada.** Com
   `avg_duration_min: 90`, um job em 38% às 08:00 deveria ter alertado por volta
   das 03:30 — não às 10:00, pela boca do cliente.
3. **Throttle explícito na reindexação** (`requests_per_second`), para que ela
   nunca compita de igual para igual com a ingestão.
4. **Rever a capacidade para carga concorrente**, com o número saindo de teste e
   não de palpite — só depois dos itens 1 a 3, para não usar hardware como
   remendo de um problema de agendamento.

**8. Lacunas de dados**

- **Nada entre 02:00 e 08:00.** É onde está a resposta para "por que a
  reindexação ficou tão para trás". Sem isso, o gatilho é conhecido no efeito e
  desconhecido na origem.
- **Sem `qps` de busca.** Impede descartar por medição direta o aumento de
  demanda de leitura.
- **Log de um único nó (`cerebro-node-3`).** Não dá para afirmar se os outros
  nós estavam no mesmo estado, nem se a reindexação estava concentrada aqui.
- **Sem métricas de merge/segmentos** e sem o tamanho configurado dos thread
  pools — o efeito do `refresh_interval: 1s` é inferido do log de throttle, não
  medido.
- **Não se sabe se a `88123` era uma retentativa** de um job anterior que falhou.

**9. Confiança global**

**Alta** para o mecanismo e para a cadeia causal: a ordenação temporal é limpa,
a escrita se move antes da leitura, e cada elo tem âncora em log ou métrica.
**Média** para a origem do gatilho — o que fez a reindexação atrasar não está
nos dados. Fechar em alta exigiria: o log entre 02:00 e 08:00, o `qps` de busca
e a confirmação de que o comportamento se repete nos demais nós.

---

## Curadoria

**A sanitização é upstream, e isso não é detalhe.** A tentação é escrever no
prompt "não use dados sensíveis" — inútil: quando o modelo lê a instrução, o log
já foi enviado. Neste pacote os vetores concretos são o nome do índice
(`logs-2026.05`, que em produção real carrega tenancy de cliente), os nomes de
nó e pod, e hostnames. Por isso a redação virou `pre_processamento` no
frontmatter, isto é, obrigação de quem preenche o parâmetro, e não regra dentro
do prompt. O roteamento para provedor sem retenção e sem treino é decisão de
compliance, com owner em segurança — não é escolha de conveniência de quem está
de plantão às 10h da manhã com o cliente reclamando.

**O passo que mudou a qualidade da saída foi o de ordenação temporal.** Sem ele
a IA entregava uma lista de correlações — heap alto, cache frio, fila cheia — em
que qualquer um dos três podia ser a causa dos outros dois. A regra "diga qual
se move primeiro e por que isso sustenta a direção da causa" é o que produz a
seção 6 com conteúdo real: o descarte do pico de busca se apoia em uma hora de
diferença entre o throttle de indexação e a primeira slow query, e em qual dos
dois thread pools satura. Isso é argumento, não opinião.

**Exigir hipóteses alternativas descartadas trouxe um efeito colateral bom.**
Ao ser forçada a defender o heap de 8g como causa e falhar, a IA produziu a
distinção entre *condição contribuinte* e *gatilho* — que é justamente o que
separa a ação certa da errada aqui. Subir o heap parece resolver e não resolve:
a próxima reindexação atrasada derruba de novo, com mais folga e o mesmo final.

**A lacuna de 02:00–08:00 é o que me impede de assinar confiança alta.** Foi
decisão consciente deixar isso explícito na seção 8 em vez de arredondar a
conclusão. Um item de playbook que sempre responde com convicção é pior do que
um que sabe dizer onde para — o plantonista precisa saber se pode agir ou se
precisa coletar mais.

**Limite conhecido.** O prompt analisa um sistema por execução. Um incidente que
atravessa Relay → Forge → Cerebro exige uma rodada por sistema mais uma síntese
manual, e essa síntese hoje não tem item na biblioteca.
