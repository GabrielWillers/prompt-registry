# Checkpoint 09 — saídas integrais dos modelos

Saída **integral** gerada por cada modelo em cada caso, como devolvida
pelo `promptfoo eval`. É o material que os asserts avaliaram.

---

## causa-raiz — gate de qualidade

### Degradação do Cerebro — pacote de artefatos do incidente — `openai:gpt-4o-mini` → **FAIL**

`13937ms · US$ 0.000713`

```
1. **Bottom line**: A causa-raiz da degradação de desempenho no sistema Cerebro foi a saturação da memória heap, resultando em rejeição de requisições e lentidão nas buscas. Nível de confiança: alta.

2. **Linha do tempo correlacionada**:
   - **08:00 UTC**: `search_p99_ms: 850 ms`, `heap_used_pct: 61%`, `cache_hit_pct: 74%`
   - **08:02 UTC**: Log de reindexação em progresso, 38% concluído.
   - **08:14 UTC**: Log de GC jovem, duração de 620 ms.
   - **08:30 UTC**: `search_p99_ms: 1100 ms`, `heap_used_pct: 68%`, `cache_hit_pct: 71%`
   - **08:41 UTC**: Log de controle de memória, começando a desacelerar a indexação.
   - **09:00 UTC**: `search_p99_ms: 2300 ms`, `heap_used_pct: 79%`, `cache_hit_pct: 58%`
   - **09:03 UTC**: Log de fila de threads de escrita cheia.
   - **09:12 UTC**: Log de GC antigo, duração de 1.1s.
   - **09:30 UTC**: `search_p99_ms: 4100 ms`, `heap_used_pct: 88%`, `cache_hit_pct: 41%`
   - **09:31 UTC**: Log de uso do circuito de memória, 86%.
   - **09:58 UTC**: Log de fila de threads de escrita cheia, rejeitando requisições.
   - **10:00 UTC**: `search_p99_ms: 6700 ms`, `heap_used_pct: 94%`, `cache_hit_pct: 29%`

3. **Cadeia causal**:
   - **Gatilho**: A execução do trabalho de reindexação às 02:00 UTC, que começou a consumir recursos significativos do sistema.
   - **Mecanismo**: O aumento do uso da memória heap, que atingiu 94% durante o período, levando a um estado de sobrecarga e rejeição de requisições.
   - **Sintomas**: Lentidão nas buscas e resultados incompletos, evidenciado pelo aumento do `search_p99_ms` e logs de erros de execução de consultas.

4. **Causa-raiz**: A saturação da memória heap devido à reindexação em andamento causou a degradação do desempenho, resultando em lentidão nas buscas e resultados incompletos.

5. **Sintomas que NÃO são a causa**:
   - O aumento no número de documentos indexados por segundo (ex. 9800 docs/s em 09:00 UTC) não é a causa, mas sim um efeito da reindexação. A causa raiz está na saturação da memória, não no volume de dados.

6. **Hipóteses alternativas descartadas**:
   - **Hipótese**: O aumento na carga de consultas foi a causa da lentidão. **Motivo**: As métricas de `indexed_docs_per_s` não mostram um aumento significativo que possa justificar a degradação observada. Além disso, a ordem temporal indica que o aumento no tempo de busca precede qualquer aumento na carga de consultas.

7. **Ação**:
   - **Contenção imediata**: Monitorar e limitar a execução de reindexações durante horários de pico de consulta para evitar saturação de recursos.
   - **Correção definitiva**: Aumentar a capacidade de memória heap ou otimizar a configuração do cluster para melhor gerenciamento de carga durante operações intensivas.

8. **Lacunas de dados**:
   - Informações sobre a carga de consultas durante a janela de incidente seriam úteis para entender melhor a interação entre reindexação e consultas.
   - Dados sobre a configuração de hardware (CPU, I/O) do cluster também ajudariam a avaliar se a infraestrutura é adequada para a carga.

9. **Confiança global**: Alta. Aumentaria com dados adicionais sobre a carga de consultas e a configuração de hardware do cluster.
```

### Degradação do Cerebro — pacote de artefatos do incidente — `google:gemini-3.1-flash-lite` → **PASS**

`10792ms · US$ 0.000749`

```
### 1. Bottom line
A causa-raiz é a execução de um *reindex job* mal dimensionado que, ao rodar fora da janela esperada, competiu por recursos de heap com as consultas de busca, levando ao esgotamento da memória (Circuit Breaker) e degradação do *query cache*. Nível de confiança: **Alta**.

---

### 2. Linha do tempo correlacionada
*   **08:00 - 08:30:** *Reindex* em progresso (log 08:02). Heap sobe de 61% para 68%. *Search p99* começa a subir (850ms -> 1100ms).
*   **09:00:** *Reindex* intensifica (logs de *throttling* 08:41). Heap atinge 79%, *cache hit* cai para 58%. *Search p99* salta para 2300ms.
*   **09:30:** *Reindex* continua (log 09:20). Heap atinge 88%. *Circuit Breaker* (parent) em 86% (log 09:31). *Search p99* atinge 4100ms.
*   **09:58 - 10:00:** Colapso total. *Write thread pool* esgotado (log 09:58). *Circuit Breaker* atinge 96% e depois 100% (log 09:58/10:01). *Search p99* chega a 6700ms com resultados parciais.

---

### 3. Cadeia causal
**Gatilho:** *Reindex job* [88123] rodando em horário de pico (iniciado às 02:00, mas ainda ativo às 09:58).
**↓**
**Mecanismo:** Consumo excessivo de *heap* pelo processo de reindexação + *throttling* de escrita, forçando o *eviction* do *query cache* (hit ratio cai de 74% para 29%) e aumentando a pressão de GC (logs 09:12, 09:58).
**↓**
**Sintomas:** Aumento do *p99* de busca (falta de cache), *EsRejectedExecutionException* (saturação de threads) e, finalmente, *CircuitBreakingException* (falha total).

---

### 4. Causa-raiz
**Configuração inadequada do *reindex job*:** O job não possui limite de taxa (*rate limiting*) nem mecanismo de *kill* automático caso ultrapasse a janela de manutenção (03:30), permitindo que ele consuma recursos críticos durante o horário de carga de produção.

---

### 5. Sintomas que NÃO são a causa
*   **Lentidão nas buscas:** É um sintoma da degradação do *query cache* e da contenção de threads, não a causa.
*   **Resultados incompletos:** É o efeito final do *Circuit Breaker* impedindo a execução de novas buscas para proteger a estabilidade do nó.

---

### 6. Hipóteses alternativas descartadas
1.  **Aumento de tráfego de escrita externo:** Descartada. O log de 08:02 mostra o *reindex* interno como o principal consumidor de recursos. O aumento de `indexed_docs_per_s` é correlato ao progresso do job, não a um pico de tráfego de usuários.
2.  **Vazamento de memória (Memory Leak):** Descartada. O heap sobe de forma linear e correlacionada com o progresso do *reindex* (logs de progresso 08:02, 09:20, 09:58). Se fosse um leak, o heap subiria independentemente da tarefa de reindexação.

---

### 7. Ação
*   **Contenção imediata:** Cancelar manualmente a tarefa de reindexação `[88123]` para liberar o *heap* e o *thread pool*.
*   **Correção definitiva:** 
    1. Implementar `requests_per_second` no *reindex API* para limitar o impacto.
    2. Adicionar um *timeout* ou *kill switch* no orquestrador do job para interrompê-lo caso ultrapasse as 06:00 UTC.
    3. Revisar o tamanho do *heap* (8GB pode ser insuficiente para o volume de dados atual + reindex).

---

### 8. Lacunas de dados
*   Não há logs de monitoramento de I/O de disco, o que ajudaria a confirmar se o *throttling* de escrita foi causado por saturação de IOPS ou apenas por pressão de memória.

---

### 9. Confiança global
**Alta.** A correlação temporal entre o progresso do *reindex* (logs), a subida do heap (métricas) e a degradação do cache/latência é inequívoca. Aumentaria a confiança com logs de I/O de disco.
```
