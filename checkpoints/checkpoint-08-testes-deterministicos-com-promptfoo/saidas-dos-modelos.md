# Checkpoint 08 — saídas integrais dos modelos

Saída **integral** gerada por cada modelo em cada caso, como devolvida
pelo `promptfoo eval`. É o material que os asserts avaliaram.

---

## nota-de-triagem

### Entrada 1 — Sentinel no teto do autoscaler — `openai:gpt-4o-mini` → **PASS**

`3929ms · US$ 0.000243`

```
ALERTA: Sentinel - autoscaler atingiu o máximo de réplicas em sentinel-api  
IMPACTO: capacidade de processamento do sentinel-api comprometida para todos os tenants  
HIPÓTESE INICIAL: aumento de 4x no volume do tenant stark-industries após onboarding de nova região  
AÇÃO IMEDIATA: análise do uso de CPU e ajuste de limites de recursos em andamento  
ESCALAR PARA: @sentinel-core se a fila no Relay continuar crescendo em 5min
```

### Entrada 1 — Sentinel no teto do autoscaler — `google:gemini-3.1-flash-lite` → **PASS**

`2522ms · US$ 0.000184`

```
ALERTA: Sentinel - esgotamento de réplicas do autoscaler (60/60)
IMPACTO: sobrecarga no Sentinel-api com acúmulo de fila no Relay a 2k/min
HIPÓTESE INICIAL: pico de tráfego do tenant stark-industries após onboarding sobrecarregou a capacidade atual
AÇÃO IMEDIATA: verificação de rate-limit para o tenant stark-industries e avaliação de aumento temporário de réplicas
ESCALAR PARA: @sentinel-core se a fila do Relay não estabilizar em 15min
```

### Entrada 2 — Relay rejeitando ingestão após deploy — `openai:gpt-4o-mini` → **PASS**

`1604ms · US$ 0.000238`

```
ALERTA: Relay - taxa de rejeição de ingestão acima de 6% por 8min  
IMPACTO: ingestão de telemetry degradada para o tenant wakanda-systems  
HIPÓTESE INICIAL: buffer saturado após deploy às 02:55 causou aumento na rejeição  
AÇÃO IMEDIATA: rollback iniciado para a versão anterior do Relay  
ESCALAR PARA: @relay-core se a rejeição não cair em 10min
```

### Entrada 2 — Relay rejeitando ingestão após deploy — `google:gemini-3.1-flash-lite` → **PASS**

`1118ms · US$ 0.000171`

```
ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão de dados degradada para o tenant wakanda-systems
HIPÓTESE INICIAL: saturação de buffer causada pelo deploy realizado às 02:55
AÇÃO IMEDIATA: rollback do deploy realizado às 02:55
ESCALAR PARA: @relay-core se a taxa de rejeição não reduzir em 10min
```

### Entrada 3 — Forge com lag de consumer subindo — `openai:gpt-4o-mini` → **PASS**

`2927ms · US$ 0.000231`

```
ALERTA: Forge - lag de ingestão acima de 9min  
IMPACTO: ingestão de dados atrasada para todos os dashboards do Sentinel  
HIPÓTESE INICIAL: falha no job anterior causou atraso no processamento do batch  
AÇÃO IMEDIATA: reiniciar o job de ingestão manualmente  
ESCALAR PARA: @data-platform se o lag não estabilizar em 10min
```

### Entrada 3 — Forge com lag de consumer subindo — `google:gemini-3.1-flash-lite` → **PASS**

`1178ms · US$ 0.000173`

```
ALERTA: Forge - consumer lag em 9min com tendência de aumento
IMPACTO: atraso no processamento do batch forge-batch-ingest e latência nos dashboards do Sentinel
HIPÓTESE INICIAL: falha no job anterior impediu a progressão normal do pipeline de ingestão
AÇÃO IMEDIATA: verificar logs de execução do job falho e reiniciar a fila de processamento
ESCALAR PARA: @data-platform se o lag não estabilizar em 15min
```

---

## triagem-de-pods

### Entrada 1 — pod reiniciando (OOMKill no carregamento do cache) — `openai:gpt-4o-mini` → **FAIL**

`7380ms · US$ 0.000308`

```
## TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: DEGRADADO — Um pod em CrashLoopBackOff.
Pods: 4 · 3 OK · 1 problema

### 1. sentinel-api-7d9c8b6f4-h4m2t — CrashLoopBackOff · severidade ALTA
- Sintoma: O pod está em estado de CrashLoopBackOff.
- Causa provável (confiança: ALTA): O pod foi finalizado devido a OOMKilled, indicando que excedeu o limite de memória.
- Evidência: "Last State: Terminated, Reason: OOMKilled", "Limits: memory: 512Mi", "high GC pressure, heap 498Mi/512Mi".
- Impacto: 1 réplica afetada, degradação parcial do serviço.
- Ação agora: Aumentar o limite de memória para o pod [requer aprovação].
- Se não resolver: Monitorar o uso de memória e considerar ajustes adicionais.

## Ações imediatas
1. Aumentar o limite de memória do pod `sentinel-api-7d9c8b6f4-h4m2t` [requer aprovação].

## Lacunas de coleta
Nenhuma relevante.
```

### Entrada 1 — pod reiniciando (OOMKill no carregamento do cache) — `google:gemini-3.1-flash-lite` → **PASS**

`3085ms · US$ 0.000371`

```
TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: DEGRADADO — A API está operando com redundância reduzida devido a falha por esgotamento de memória.
Pods: 4 · 3 OK · 1 problema

### 1. sentinel-api-7d9c8b6f4-h4m2t — CrashLoopBackOff · severidade ALTA
- Sintoma: Reinicializações frequentes (14 em 42m) com morte do processo ao carregar cache.
- Causa provável (confiança: ALTA): Estouro de limite de memória (OOMKilled) devido à carga de cache exceder os 512Mi definidos.
- Evidência: `Reason: OOMKilled`, `heap 498Mi/512Mi`, `[FATAL] [runtime] out of memory`.
- Impacto: Perda de 50% das réplicas da `sentinel-api`; degradação parcial na disponibilidade/latência da API.
- Ação agora: Solicitar aumento temporário dos limites de memória via `kubectl edit deployment sentinel-api` [requer aprovação].
- Se não resolver: Verificar se houve aumento recente no volume de alertas que o cache processa ou analisar heap dump.

## Ações imediatas
1. Avaliar com o time de engenharia se o aumento da memória (`requests/limits`) é seguro para o nó ou se houve uma anomalia na carga de alertas.
2. Executar `kubectl edit deployment sentinel-api -n sentinel-prod` para ajustar o limite de memória para, por exemplo, 768Mi ou 1Gi [requer aprovação].
3. Monitorar a estabilidade do pod após a aplicação da nova configuração.

## Lacunas de coleta
Nenhuma relevante; os logs e o evento OOMKilled são conclusivos para o diagnóstico atual.
```

### Entrada 2 — pods que não sobem (tag inexistente + falta de CPU) — `openai:gpt-4o-mini` → **FAIL**

`10310ms · US$ 0.000395`

```
## TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: DEGRADADO — dois pods em estado problemático.
Pods: 4 · 2 OK · 2 problema

### 1. sentinel-api-7d9c8b6f4-zzp10 — ImagePullBackOff · severidade ALTA
- Sintoma: O pod não está pronto e está em estado de espera.
- Causa provável (confiança: ALTA): Falha ao puxar a imagem do registro, possivelmente a imagem não existe.
- Evidência: "Failed to pull image 'registry.aegis.io/sentinel-api:2.9.2': manifest unknown", "Error: ErrImagePull".
- Impacto: 1 réplica afetada, degradação total do serviço relacionado ao pod.
- Ação agora: Verificar a existência da imagem no registro e corrigir a referência da imagem [requer aprovação].

### 2. sentinel-ingest-8f7a9c5b-4dkqm — Pending · severidade ALTA
- Sintoma: O pod não está pronto e está em estado de espera.
- Causa provável (confiança: ALTA): Falta de recursos de CPU disponíveis para agendar o pod.
- Evidência: "0/6 nodes are available: 6 Insufficient cpu", "State: Waiting, Reason: Pending".
- Impacto: 1 réplica afetada, degradação total do serviço relacionado ao pod.
- Ação agora: Avaliar a utilização de CPU dos nós e considerar a liberação de recursos ou aumentar a capacidade do cluster [requer aprovação].

## Ações imediatas
1. Verificar a existência da imagem `registry.aegis.io/sentinel-api:2.9.2` e corrigir a referência da imagem.
2. Avaliar a utilização de CPU dos nós e considerar a liberação de recursos ou aumentar a capacidade do cluster.

## Lacunas de coleta
Nenhuma relevante.
```

### Entrada 2 — pods que não sobem (tag inexistente + falta de CPU) — `google:gemini-3.1-flash-lite` → **FAIL**

`12890ms · US$ 0.000428`

```
TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: DEGRADADO — O serviço API está com capacidade reduzida e o serviço Ingest está totalmente indisponível.
Pods: 4 · 2 OK · 2 problema

### 1. sentinel-ingest-8f7a9c5b-4dkqm — Pending · severidade ALTA
- Sintoma: Pod não escala/inicia.
- Causa provável (confiança: alta): Esgotamento de recursos no cluster (CPU).
- Evidência: "FailedScheduling", "0/6 nodes are available: 6 Insufficient cpu".
- Impacto: Total. Nenhuma réplica do serviço `sentinel-ingest` está rodando.
- Ação agora: Verificar `kubectl top nodes` para confirmar carga; [requer aprovação] escalar cluster ou reduzir requests de CPU de pods não críticos.
- Se não resolver: Revisar quotas do namespace ou listar pods de prioridade baixa para eventual despejo (eviction).

### 2. sentinel-api-7d9c8b6f4-zzp10 — ImagePullBackOff · severidade MÉDIA
- Sintoma: Pod falha ao subir após tentativa de novo deploy.
- Causa provável (confiança: alta): Falha de referência na imagem ou erro no registry (tag não encontrada).
- Evidência: "manifest unknown", "Failed to pull image ... sentinel-api:2.9.2".
- Impacto: Parcial. O serviço `sentinel-api` opera com 50% da capacidade (1 de 2 réplicas).
- Ação agora: Verificar se a tag `2.9.2` existe no repositório; [requer aprovação] realizar rollback para a versão anterior estável (`kubectl rollout undo deployment/sentinel-api`).
- Se não resolver: Verificar permissões de rede/auth do node com o registry.

## Ações imediatas
1. Validar disponibilidade da imagem `registry.aegis.io/sentinel-api:2.9.2` via CLI ou console do registry.
2. Executar rollback do `sentinel-api` se a imagem não estiver acessível.
3. Analisar consumo de recursos (`kubectl top nodes`) para diagnosticar o erro de `Insufficient cpu` no `sentinel-ingest`.

## Lacunas de coleta
- `kubectl top nodes`: Necessário para confirmar se a falta de CPU é real ou causada por pods "zumbis".
- `kubectl get nodes`: Necessário para verificar se há nós em estado `NotReady` reduzindo a capacidade total.
```

### Entrada 3 — tudo saudável (não pode inventar problema) — `google:gemini-3.1-flash-lite` → **FAIL**

`7114ms · US$ 0.000232`

```
TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: SAUDÁVEL — Todos os pods estão em estado Running e prontos para atender requisições sem indícios de instabilidade recente.
Pods: 4 · 4 OK · 0 problema

Nenhum pod apresenta status crítico, falhas de prontidão ou restarts em janela recente (últimos 60 minutos). O serviço está estável.

Nenhuma ação necessária para o plantão.

## Ações imediatas
Nenhuma.

## Lacunas de coleta
Nenhuma relevante.
```

### Entrada 3 — tudo saudável (não pode inventar problema) — `openai:gpt-4o-mini` → **PASS**

`2481ms · US$ 0.000204`

```
## TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: SAUDÁVEL — todos os pods estão em estado normal.
Pods: 4 · 4 OK · 0 problema

Todos os pods estão com status Running, prontos e sem reinícios recentes. Os logs do pod `sentinel-api-7d9c8b6f4-2xk9p` indicam que a aplicação está operando normalmente, com checagens de saúde bem-sucedidas e sem erros registrados.

Nenhuma ação necessária para o plantão.
```

---

## networkpolicy-sentinel

### Manifesto allow-all do Sentinel + padrão da Aegis + mapa de serviços — `openai:gpt-4o-mini` → **FAIL**

`15478ms · US$ 0.000616`

```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-default-deny
  namespace: sentinel-prod
spec:
  podSelector: {}  # Política default-deny para todos os pods do namespace
  policyTypes:
    - Ingress
    - Egress

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow-ingress
  namespace: sentinel-prod
spec:
  podSelector: { matchLabels: { app: sentinel } }  # Aplica apenas aos pods do Sentinel
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector: { matchLabels: { name: relay-prod } }  # Permite tráfego do Relay
          podSelector: { matchLabels: { app: relay } }  # Permite tráfego do Relay
      # Permite tráfego de entrada do Relay (consumo de eventos)
    - from:
        - namespaceSelector: { matchLabels: { name: edge } }  # Permite tráfego do API gateway
          podSelector: { matchLabels: { app: api-gateway } }  # Permite tráfego do API gateway
      # Permite tráfego de entrada do gateway de API da plataforma

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow-egress
  namespace: sentinel-prod
spec:
  podSelector: { matchLabels: { app: sentinel } }  # Aplica apenas aos pods do Sentinel
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: { matchLabels: { name: forge-prod } }  # Permite tráfego para o Forge
          podSelector: { matchLabels: { app: forge } }  # Permite tráfego para o Forge
      ports:
        - port: 5432  # Porta do warehouse
      # Permite saída para o Forge (warehouse, porta 5432)
    - to:
        - namespaceSelector: { matchLabels: { name: cerebro-prod } }  # Permite tráfego para o Cerebro
          podSelector: { matchLabels: { app: cerebro } }  # Permite tráfego para o Cerebro
      ports:
        - port: 9200  # Porta do Elasticsearch
      # Permite saída para o Cerebro (busca, porta 9200)
    - to:
        - namespaceSelector: { matchLabels: { name: kube-system } }  # Permite tráfego para o DNS interno
          podSelector: { matchLabels: { k8s-app: kube-dns } }  # Permite tráfego para o DNS interno
      ports:
        - port: 53  # Porta do DNS
        - protocol: UDP  # Permite UDP para DNS
        - protocol: TCP  # Permite TCP para DNS
      # Permite saída para DNS interno

PENDÊNCIAS:
- Nenhuma pendência identificada.

AUTOVERIFICAÇÃO:
- Existe default-deny explícito para ingress e egress? PASSA - Política default-deny explícita foi criada.
- Toda origem de ingress está no padrão? Alguma sobrou de fora? PASSA - Todas as origens de ingress estão no padrão.
- Todo destino de egress está no padrão? Nenhum a mais? PASSA - Todos os destinos de egress estão no padrão.
- DNS está liberado no egress, em UDP e TCP na porta 53? PASSA - DNS está liberado em ambas as portas e protocolos.
- Cada peer usa `namespaceSelector` + `podSelector` do mapa, no mesmo item de lista? PASSA - Todos os peers seguem a regra corretamente.
- Alguma porta ou label foi inventada? PASSA - Todas as portas e labels estão de acordo com o mapa de serviços.
- Sobrou algum `- {}` ou seletor vazio indevido? PASSA - Nenhum `- {}` ou seletor vazio indevido foi utilizado.
```
```

### Manifesto allow-all do Sentinel + padrão da Aegis + mapa de serviços — `google:gemini-3.1-flash-lite` → **PASS**

`2961ms · US$ 0.000434`

```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-hardened-policy
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes:
  - Ingress
  - Egress
  # Default Deny implícito (ao não incluir ingress/egress, blocos vazios são tratados como deny)
  # Regra de Ingress
  ingress:
  - from: # Permite tráfego do Relay
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: relay-prod
      podSelector:
        matchLabels:
          app: relay
  - from: # Permite tráfego do API Gateway
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: edge
      podSelector:
        matchLabels:
          app: api-gateway
  # Regras de Egress
  egress:
  - to: # Acesso ao Forge (Postgres)
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: forge-prod
      podSelector:
        matchLabels:
          app: forge
    ports:
    - protocol: TCP
      port: 5432
  - to: # Acesso ao Cerebro (Elasticsearch)
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cerebro-prod
      podSelector:
        matchLabels:
          app: cerebro
    ports:
    - protocol: TCP
      port: 9200
  - to: # Acesso ao DNS Interno (CoreDNS)
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### PENDÊNCIAS
Nenhuma pendência encontrada. Todos os fluxos solicitados no padrão possuem mapeamento correspondente no `<mapa_de_servicos>`.

### AUTOVERIFICAÇÃO
- **Existe default-deny explícito para ingress e egress?** PASSA. A estrutura da política com seletores definidos nega todo tráfego não listado.
- **Toda origem de ingress está no padrão? Alguma sobrou de fora?** PASSA. Apenas Relay e API Gateway foram liberados.
- **Todo destino de egress está no padrão? Nenhum a mais?** PASSA. Apenas Forge, Cerebro e DNS foram incluídos.
- **DNS está liberado no egress, em UDP e TCP na porta 53?** PASSA. Ambos os protocolos foram incluídos na regra de egress para o `kube-dns`.
- **Cada peer usa namespaceSelector + podSelector do mapa, no mesmo item de lista?** PASSA. Estruturados corretamente para garantir a lógica AND.
- **Alguma porta ou label foi inventada?** PASSA. Foram utilizados exclusivamente os dados do `<mapa_de_servicos>`.
- **Sobrou algum `- {}` ou seletor vazio indevido?** PASSA. Todos os seletores foram preenchidos conforme as especificações de identidade dos serviços.
```
