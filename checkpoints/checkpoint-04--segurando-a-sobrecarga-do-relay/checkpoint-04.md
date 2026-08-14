# Checkpoint 04 — Segurando a sobrecarga do Relay

Construído por meta-prompting em três rodadas. A primeira pediu à IA um prompt de
recomendação de estratégia de backpressure, e o resultado foi um prompt que
produzia resposta única e confiante — exatamente o que o enunciado diz para
evitar. Na segunda rodada pedi que ela criticasse o próprio prompt procurando
onde ele permitiria recomendar sem comparar, e a crítica apontou a ausência de
qualquer passo que obrigasse a avaliar mais de um caminho. A terceira rodada
gerou o método em seis passos, e a curadoria manual entrou no passo 2 — a
classificação de restrições em duras e brandas, que é o que faz a comparação ter
consequência em vez de virar tabela decorativa.

Uma decisão de escopo: o prompt saiu **agnóstico de domínio**. Ele nasceu do
problema de backpressure do Relay, mas nada nele fala de fila ou de barramento.
O que entra na biblioteca é o método de decisão sob restrições conflitantes; o
cenário do Relay é só o primeiro caso de uso.

### 1. Prompt parametrizável

```
[ROLE]
Você é arquiteto(a) de sistemas distribuídos sênior atuando como consultor de
decisão. Seu trabalho NÃO é dar a primeira resposta plausível, mas comparar
caminhos alternativos, expor o preço de cada um e recomendar com o raciocínio à
mostra. Decisões de arquitetura são caras de reverter — trate cada trade-off com rigor.

[CONTEXTO — parâmetros]
- Sistema em questão: {{SISTEMA}}
- Estado atual (fatos medidos): {{ESTADO_ATUAL}}
- Restrições que a solução DEVE respeitar: {{RESTRICOES}}
- Opções candidatas já em cima da mesa (pode vir vazio): {{OPCOES_CANDIDATAS}}
- Contexto/histórico relevante: {{CONTEXTO_ADICIONAL}}

[TAREFA]
Recomendar uma estratégia (ou combinação) para o problema descrito, escolhendo
entre as opções candidatas e/ou propondo outras defensáveis, sempre justificando
contra as restrições.

[MÉTODO — siga nesta ordem, pensando passo a passo]
1. Reformule o problema em UMA frase (confirmar entendimento).
2. Classifique as restrições em DURAS (invioláveis — violar = solução inválida) e
   BRANDAS (toleram degradação / têm folga). Aponte qual é o GARGALO REAL que
   aperta a decisão.
3. Monte o conjunto de opções: as candidatas recebidas + quaisquer outras
   defensáveis. Mínimo de 3.
4. Avalie CADA opção:
   - como funciona (1 linha);
   - contra CADA restrição dura: satisfaz ou viola? (viola qualquer dura → eliminada);
   - custo (infra, complexidade operacional, risco de implementação);
   - o que ela NÃO resolve.
5. Compare as sobreviventes numa TABELA (colunas = restrições duras + custo + risco).
6. Recomende (opção única OU combinação). Deixe explícito:
   - o que otimiza e o que SACRIFICA;
   - por que vence as alternativas que você NÃO escolheu;
   - premissas assumidas;
   - o GATILHO DE REVISÃO: o que faria mudar a recomendação.

[REGRAS DE RACIOCÍNIO]
- Violou restrição dura → está fora. Não recomende "com ressalvas".
- Não invente números ausentes do estado atual. Dado que faltar vira premissa listada.
- Não assuma tecnologia específica que não esteja no estado atual ou no contexto.
  Se o estado diz "barramento de eventos", não trate como se fosse um produto
  nomeado nem importe features dele como dadas.
- Prefira a solução mais simples que satisfaça as restrições; só adicione
  complexidade se ela comprar algo necessário.
- Combinações são permitidas e às vezes preferíveis, mas cada peça precisa
  justificar seu custo.

[FORMATO DE SAÍDA]
1. Problema em uma frase
2. Restrições classificadas (duras / brandas) + gargalo real
3. Tabela comparativa
4. Recomendação + o que sacrifica
5. Premissas
6. Gatilho de revisão
```

---

### 2. Execução (modelo e output)

**Modelo:** Claude Opus 4.8. Parâmetros preenchidos com o cenário do Relay.

**Por que este modelo.** Decisão de arquitetura é cara de reverter, e o valor
está em comparar caminhos e enxergar o que cada um sacrifica — raciocínio
comparativo, o oposto de extração. O volume é o menor de toda a biblioteca: uma
execução por decisão, talvez uma por trimestre. Com esse volume, custo por token
é irrelevante e latência não existe como critério; a única variável que importa é
qualidade do raciocínio. **Privacidade:** o cenário aqui é arquitetura interna e
número de SLA, sem dado de cliente — é o item de menor sensibilidade do playbook,
e o único que eu rodaria num provedor sem exigência de retenção zero.

**1. Problema em uma frase**
Durante rajadas de um cliente grande, a fila única do Relay faz o alerting em tempo real do Sentinel esperar atrás da ingestão em massa do Forge, atrasando alertas com SLA de 60s.

**2. Restrições classificadas**
- **Duras:** não perder telemetry; alerting do Sentinel ≤ 60s (SLA).
- **Brandas:** ingestão do Forge pode atrasar até 15min (folga); orçamento 8% acima (penaliza, não elimina).
- **Gargalo real:** a assimetria 60s (Sentinel) × 15min (Forge). Na fila compartilhada, o volume do Forge starva o caminho de alerta. Os 15min de folga são a alavanca.

**3. Tabela comparativa**

| Opção | Não perde msg? | Protege os 60s? | Custo infra | Risco/complexidade |
|---|---|---|---|---|
| Prioridade ao Sentinel (lanes separadas) | Sim | **Sim, direto** | Baixo | Baixo |
| Partição por cliente (bulkhead) | Sim | Parcial (isola o barulhento; dentro da partição ainda precisa de prioridade) | Médio | Médio |
| Auto-scaling de consumidores | Sim | Parcial — *lag* de spin-up (rajada de 25min pode acabar antes) | **Alto (fura orçamento)** | Médio |
| Dead-letter queue | Sim (preserva) | **Não** — DLQ é para msg envenenada, não overflow | Baixo | Resolve o problema errado |

**4. Recomendação + o que sacrifica**
Combinação liderada por **prioridade ao Sentinel (lanes separadas)**: isolar o stream de alerting da ingestão em massa do Forge, protegendo os 60s independentemente do backlog do Forge — mudança mais barata que ataca o gargalo real e cabe no orçamento. Complemento: **partição por cliente** para isolar o cliente barulhento (causa do incidente), médio prazo. Rede de segurança: **DLQ** só para mensagens não-processáveis, não como balde de overflow. Auto-scaling apenas *limitado* no lado Forge para drenar backlog dentro dos 15min — nunca como defesa dos 60s.

Sacrifica, de propósito: latência de ingestão do Forge durante rajadas (até os 15min) e horas de engenharia na partição.

**5. Premissas**
- O Relay suporta consumer groups / roteamento por prioridade sem reescrita completa.
- Forge absorve a rajada de catch-up dentro dos 15min.
- 4h de retenção comportam o backlog de uma rajada de 25min sem perda.

**6. Gatilho de revisão**
Se as rajadas virarem carga sustentada acima de 180k/s, ou se o cliente barulhento passar a ser vários ao mesmo tempo (a partição para de isolar), então capacidade extra vira inevitável, orçamento ou não.

---

### 3. Curadoria

Sem a etapa de classificar restrições duras × brandas, a saída inicial tratava "não perder mensagem" e "orçamento estourado" com peso igual e chegava a sugerir auto-scaling como carro-chefe — justamente a opção que fura a restrição financeira. Forçar a classificação faz o "não perder" *eliminar* candidatos e o "orçamento" apenas *penalizá-los* — a hierarquia certa.

O melhor sinal de que o método funciona é a DLQ: um prompt ingênuo aceita "guarda o overflow e reprocessa depois" como resposta boa. Os campos "protege os 60s?" e "o que ela NÃO resolve" fizeram o modelo perceber sozinho que DLQ não reduz a latência do stream vivo — ela existe para mensagem envenenada, não para backpressure.

Dois campos que adicionei e recomendo manter: **"por que vence as que descartou"** (mata a tendência de só elogiar a própria escolha) e **"gatilho de revisão"** (torna a recomendação datada e falseável).

Watch-out para reuso: o modelo tende a assumir que "barramento de eventos" = Kafka e importar features específicas como dadas. A regra "não invente fatos ausentes" mantém o prompt tech-agnóstico. Respostas Kafka-específicas entram via `{{CONTEXTO_ADICIONAL}}`, não hardcoded.