# Checkpoint 08 — Testes determinísticos com promptfoo

Cada prompt de saída estruturada ganhou um `promptfooconfig.yaml` ao lado do
`prompt.md`, na própria pasta do prompt. O teste viaja junto com o prompt.

| Prompt | Config | Casos |
|---|---|---|
| nota-de-triagem | [`devops/nota-de-triagem/promptfooconfig.yaml`](../../devops/nota-de-triagem/promptfooconfig.yaml) | 3 alertas crus do CP02 |
| triagem-de-pods | [`devops/triagem-de-pods/promptfooconfig.yaml`](../../devops/triagem-de-pods/promptfooconfig.yaml) | 3 snapshots do CP01 |
| networkpolicy-sentinel | [`devops/networkpolicy-sentinel/promptfooconfig.yaml`](../../devops/networkpolicy-sentinel/promptfooconfig.yaml) | manifesto + padrão + mapa do CP06 |

Os três prompts de saída aberta — causa-raiz (CP03), decisão de arquitetura
(CP04) e a cadeia de migração (CP05) — ficam de fora por definição: não têm
resposta única verificável por regex. Eles são o escopo da camada de julgamento
do CP09.

**Ambiente de execução:** promptfoo 0.122.0, Node 22.23.2. Providers
`openai:gpt-4o-mini` e `google:gemini-3.1-flash-lite`.

---

## 1. Os três arquivos de configuração

### nota-de-triagem

```yaml
# yaml-language-server: $schema=https://promptfoo.dev/config-schema.json
description: nota-de-triagem — nota padronizada de 5 campos a partir de um alerta cru

prompts:
  - file://prompt.md

providers:
  - openai:gpt-4o-mini
  - id: google:gemini-3.1-flash-lite
    config:
      inputCost: 0.0000001 # US$ 0,10 / 1M tokens
      outputCost: 0.0000004 # US$ 0,40 / 1M tokens
      generationConfig:
        thinkingConfig:
          thinkingBudget: 0

defaultTest:
  vars:
    mapa_escalonamento: '' # exercita o caminho do default embutido no prompt
    contexto_plataforma: >-
      Relay: ingestão/barramento de eventos. Forge: pipeline de dados e data
      warehouse. Sentinel: observabilidade e alerting. Cerebro: indexação e busca.
  assert:
    - { type: contains, value: 'ALERTA:' }
    - { type: contains, value: 'IMPACTO:' }
    - { type: contains, value: 'HIPÓTESE INICIAL:' }
    - { type: contains, value: 'AÇÃO IMEDIATA:' }
    - { type: contains, value: 'ESCALAR PARA:' }
    - type: regex
      value: 'ESCALAR PARA:.*@\w+'
    - type: javascript
      value: |
        const linhas = String(output).trim().split('\n').filter((l) => l.trim() !== '');
        if (linhas.length > 8) {
          return { pass: false, score: 0, reason: `nota com ${linhas.length} linhas (máximo 8)` };
        }
        return true;
    - { type: latency, threshold: 5000 }
    - { type: cost, threshold: 0.01 }

tests:
  - description: Entrada 1 — Sentinel no teto do autoscaler
    vars:
      alerta_cru: >-
        2026-05-12 14:02:09 UTC [Sentinel] autoscaler hit max replicas (60/60) on sentinel-api,
        queue depth on Relay growing 2k/min, CPU avg 88%, tenant stark-industries
        sending 4x baseline volume after onboarding new region
    assert:
      - { type: contains, value: Sentinel }

  - description: Entrada 2 — Relay rejeitando ingestão após deploy
    vars:
      alerta_cru: >-
        2026-05-13 03:11:00 UTC [Relay] ingest reject rate 6% for 8min, tenant wakanda-systems,
        buffer saturated after deploy 02:55
    assert:
      - { type: contains, value: Relay }
      - { type: contains, value: '02:55' }   # a hipótese cita o deploy do alerta...
      - { type: not-contains, value: '09:14' } # ...e não o do exemplo de estilo

  - description: Entrada 3 — Forge com lag de consumer subindo
    vars:
      alerta_cru: >-
        2026-05-13 11:40:22 UTC [Forge] consumer lag 9min and climbing, batch forge-batch-ingest
        delayed after previous job failure, downstream Sentinel starting to lag
    assert:
      - { type: contains, value: Forge }
      - { type: not-contains, value: acme-corp }
```

Os asserts de `02:55` / `09:14` e de `acme-corp` não estavam no enunciado. Eu os
acrescentei porque testam a correção específica do CP02: o prompt tem três
exemplos de estilo embutidos, e o risco real é o modelo copiar conteúdo deles.
`09:14` e `acme-corp` só existem nos exemplos. Se aparecerem na saída, houve
contaminação por few-shot — e agora isso é um teste, não uma esperança.

### triagem-de-pods

Estrutura igual. Os `vars` fixos (`namespace`, `cluster`, `janela_coleta`,
`contexto_operacional`, `politica_acao`) ficam em `defaultTest`; só o `snapshot`
varia por caso. Asserts específicos:

```yaml
# Entrada 1 — cita o pod e chega à causa, não ao status
- { type: contains, value: sentinel-api-7d9c8b6f4-h4m2t }
- type: javascript
  value: |
    if (!/OOMKilled|mem[óo]ria/i.test(String(output))) {
      return { pass: false, score: 0, reason: 'não citou a causa (OOMKilled / memória)' };
    }
    return true;

# Entrada 2 — os DOIS pods problemáticos e as DUAS causas
- { type: contains, value: sentinel-api-7d9c8b6f4-zzp10 }
- { type: contains, value: sentinel-ingest-8f7a9c5b-4dkqm }
- /2\.9\.2|ImagePullBackOff/i     (javascript)
- /insufficient|cpu/i             (javascript)

# Entrada 3 — saudável: sinaliza que não há problema...
- /SAUD[ÁA]VEL|nenhum[ao]?\s+(pod\s+)?(problem|a[çc][ãa]o)/i   (javascript)
# ...e não classifica nenhum pod como em falha
- type: javascript
  value: |
    const falhas = ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull', 'OOMKilled', 'Pending'];
    const achados = falhas.filter((f) => String(output).includes(f));
    if (achados.length > 0) {
      return { pass: false, score: 0,
        reason: `classificou pod em falha num cluster saudável: ${achados.join(', ')}` };
    }
    return true;
```

### networkpolicy-sentinel

```yaml
# é uma NetworkPolicy com os dois policyTypes
- { type: contains, value: 'kind: NetworkPolicy' }
- type: javascript
  value: |
    const bloco = String(output).match(/policyTypes:[\s\S]{0,120}/g) || [];
    if (!bloco.some((b) => /Ingress/.test(b) && /Egress/.test(b))) {
      return { pass: false, score: 0, reason: 'policyTypes não contém Ingress e Egress juntos' };
    }
    return true;

# nenhuma regra allow-all DENTRO da política gerada
- type: javascript
  value: |
    const t = String(output);
    const corte = t.search(/^#*\s*(###\s*)?\d*\.?\s*(PEND[ÊE]NCIAS|AUTOVERIFICA)/im);
    const yaml = corte > 0 ? t.slice(0, corte) : t;
    if (/-\s*\{\}/.test(yaml)) {
      return { pass: false, score: 0, reason: 'regra allow-all "- {}" na política gerada' };
    }
    return true;

# egress libera Forge (5432) e Cerebro (9200); ingress libera o Relay
- { type: regex, value: 'port:\s*5432' }
- { type: regex, value: 'port:\s*9200' }
- { type: contains, value: 'app: forge' }
- { type: contains, value: 'app: cerebro' }
- { type: contains, value: 'app: relay' }

# toda regra tem comentário — em qualquer posição do bloco
- type: javascript   # (implementação completa no arquivo)

# extra meu: não inventar identidade de namespace
- type: javascript
  value: |
    const ns = [...yaml.matchAll(/namespaceSelector:\s*\{?\s*matchLabels:\s*\{?\s*([\w./-]+)\s*:/g)];
    const ruins = ns.map((m) => m[1]).filter((k) => k !== 'kubernetes.io/metadata.name');
    if (ruins.length > 0) {
      return { pass: false, score: 0,
        reason: `namespaceSelector com label inventada: ${[...new Set(ruins)].join(', ')}` };
    }
    return true;
```

---

## 2. Execução — `promptfoo eval`

Tabela de pass/fail em [`saida-promptfoo-eval.txt`](./saida-promptfoo-eval.txt).
As **saídas integrais dos modelos** — o texto que os asserts avaliaram, nos 14
pares caso × provider — estão em [`saidas-dos-modelos.md`](./saidas-dos-modelos.md).

### nota-de-triagem — 6/6

| | provider | caso | latência | custo |
|---|---|---|---|---|
| PASS | gpt-4o-mini | Entrada 1 — Sentinel no teto do autoscaler | 3929ms | $0,000243 |
| PASS | gemini-3.1-flash-lite | Entrada 1 | 2522ms | $0,000184 |
| PASS | gpt-4o-mini | Entrada 2 — Relay rejeitando ingestão | 1604ms | $0,000238 |
| PASS | gemini-3.1-flash-lite | Entrada 2 | 1118ms | $0,000171 |
| PASS | gpt-4o-mini | Entrada 3 — Forge com lag de consumer | 2927ms | $0,000231 |
| PASS | gemini-3.1-flash-lite | Entrada 3 | 1178ms | $0,000173 |

### triagem-de-pods — 2/6 (todas as falhas são de latência)

| | provider | caso | latência | custo |
|---|---|---|---|---|
| **FAIL** | gpt-4o-mini | Entrada 1 — pod reiniciando | **7380ms** | $0,000308 |
| PASS | gemini-3.1-flash-lite | Entrada 1 | 3085ms | $0,000371 |
| **FAIL** | gpt-4o-mini | Entrada 2 — pods que não sobem | **10310ms** | $0,000395 |
| **FAIL** | gemini-3.1-flash-lite | Entrada 2 | **12890ms** | $0,000428 |
| **FAIL** | gemini-3.1-flash-lite | Entrada 3 — tudo saudável | **7114ms** | $0,000232 |
| PASS | gpt-4o-mini | Entrada 3 | 2481ms | $0,000204 |

### networkpolicy-sentinel — 1/2

| | provider | caso | latência | custo |
|---|---|---|---|---|
| **FAIL** | gpt-4o-mini | Manifesto allow-all | **15478ms** | $0,000616 |
| PASS | gemini-3.1-flash-lite | Manifesto allow-all | 2961ms | $0,000434 |

Falhas do `gpt-4o-mini`:
- `latency`: 15478ms contra o teto de 5000ms;
- `javascript`: **namespaceSelector com label inventada: `name`**.

### Consolidado por tipo de assert

| assert | execuções | falhas |
|---|---|---|
| contains | 52 | 0 |
| regex | 10 | 0 |
| not-contains | 4 | 0 |
| javascript | 24 | 1 |
| cost | 14 | 0 |
| **latency** | 14 | **5** |

118 execuções de assert, 6 falhas. Cinco são latência. Uma é conteúdo.

---

## 3. Curadoria

### O único defeito de conteúdo que a suíte encontrou

O `gpt-4o-mini` escreveu, na NetworkPolicy:

```yaml
- namespaceSelector: { matchLabels: { name: relay-prod } }
```

A label é `name`. O mapa de serviços do CP06 dá o **nome** do namespace
(`relay-prod`), e a label que o Kubernetes popula sozinho para isso é
`kubernetes.io/metadata.name`. Escrever `name: relay-prod` inventa uma label que
o cluster pode não ter — e o efeito é o pior possível: **o manifesto aplica sem
erro e o seletor não casa nada**. A política parece instalada e não protege
(ou, no egress, corta a conectividade). É exatamente a classe de falha
silenciosa que a regra 2 do prompt existe para impedir, e o Gemini respeitou.

Esse assert não estava no enunciado. Acrescentei depois de ler a saída, e é o
que mais valor entregou: dos 118 asserts executados, foi o único que pegou um
defeito real de produção. Os requisitos do enunciado verificam que o **conteúdo
certo está presente**; este verifica que **o conteúdo errado não está**. As duas
perguntas são diferentes, e a segunda é a que pega regressão.

### Três asserts meus estavam errados antes de qualquer prompt estar

Vale registrar porque é o erro clássico de quem começa a testar prompt: culpar o
modelo pelo teste mal escrito.

1. **`(?i)` não existe em regex JavaScript.** O motor do promptfoo é o
   `RegExp` do V8, e `'(?i)(OOMKilled|memória)'` quebra com *Invalid group* —
   erro de teste, reportado como falha do prompt. Migrei para assert
   `javascript` com `/…/i`, que além de funcionar deixa escrever a mensagem de
   falha em português e específica.

2. **`not-contains: '- {}'` sobre a saída inteira.** O prompt do CP06 termina
   com uma seção de AUTOVERIFICAÇÃO em que o modelo responde à pergunta
   *"sobrou algum `- {}`?"* — citando a string. O assert ingênuo lia essa
   citação e **reprovava uma política correta**. Escopei a verificação à região
   do manifesto, cortando antes de PENDÊNCIAS/AUTOVERIFICAÇÃO. Lição: quando o
   prompt produz saída em seções, o assert precisa saber em qual seção olhar.

3. **Comentário de regra só na mesma linha.** Eu exigia `- from: # …`. O Gemini
   comenta na linha **acima**, o `gpt-4o-mini` comenta na linha **abaixo** do
   bloco. Os três são YAML idiomático e os três cumprem o padrão da Aegis. O
   assert reprovava por estilo, não por substância. Reescrevi para aceitar
   comentário em qualquer posição do bloco da regra. Um teste que impõe estilo
   além do que o padrão pede vira atrito e acaba desativado.

Em nenhum dos três casos eu mexi no prompt. O teste é que estava errado — e
descobrir isso é metade do trabalho deste checkpoint.

### Latência e custo: os dois limites se comportam de forma oposta

**Custo nunca foi problema.** O pior caso foi US$ 0,000616, **16 vezes abaixo**
do teto de US$ 0,01. Nos dois providers, nos três prompts. Com modelos dessa
faixa, o gate de custo não seleciona nada — ele é uma rede de segurança contra
trocar o modelo por um caro sem perceber, e é bom que exista por isso, mas não
influencia a escolha hoje.

**Latência reprovou 5 de 14 chamadas**, e é aqui que a escolha de modelo dói.
Os números organizam-se por tamanho de saída, não por dificuldade da tarefa:

| Prompt | Tokens de saída | Latência | Resultado |
|---|---|---|---|
| nota-de-triagem | ~90 (5 linhas) | 1,1–3,9s | 6/6 passa |
| triagem-de-pods | ~400–600 | 2,5–12,9s | instável |
| networkpolicy-sentinel | ~1100 (YAML) | 3,0–15,5s | falha no gpt-4o-mini |

O gate de 5s não mede qualidade do modelo — **mede quanto texto o prompt manda
gerar**. A `nota-de-triagem` passa sempre porque produz cinco linhas. A
NetworkPolicy falha no `gpt-4o-mini` porque produz cem linhas de YAML mais
pendências mais autoverificação, e nenhum modelo cospe isso em 5s.

E a instabilidade é real: a mesma Entrada 2 da triagem deu 8257ms numa rodada e
10310ms na seguinte no `gpt-4o-mini`; a Entrada 3 deu 7232ms e 7114ms no Gemini,
mas 1900ms e 2481ms no `gpt-4o-mini`. Não há um vencedor — há variância de rede
e de fila que o `latency` mede junto com o modelo. Numa rodada anterior registrei
um outlier de **254 segundos** numa chamada que normalmente leva 1,4s: era stall
de rede, e o assert reportou como falha de latência do prompt.

**O que eu faria numa biblioteca de verdade**, e que fica registrado como
recomendação e não como mudança (o enunciado fixa os 5s):

- manter 5s para prompts de saída curta, onde o limite é significativo;
- subir para 20–30s nos prompts de geração longa, ou trocar o gate por
  **tokens de saída**, que é a variável que o prompt de fato controla;
- medir latência como **mediana de N execuções**, nunca como amostra única —
  um gate determinístico sobre uma métrica de cauda longa produz teste
  intermitente, e teste intermitente é desativado pelo time em duas semanas.

### O ajuste que salvou o gate de latência no Gemini

O `gemini-3.5-flash` reprovava por latência em quase tudo (6474ms na
`nota-de-triagem`, que é o prompt mais curto). O motivo apareceu no
`tokenUsage`: 60 tokens de *reasoning* numa tarefa de preencher cinco campos.
Desliguei o thinking:

```yaml
generationConfig:
  thinkingConfig:
    thinkingBudget: 0
```

Resultado medido: **6474ms → 1572ms** e custo de $0,0039 → $0,00037, sem
diferença de qualidade — todos os asserts de conteúdo continuaram passando. A
decisão é defensável em geral: os três prompts testados aqui são de **formatação
determinística**, não de raciocínio. Pagar tokens de pensamento para preencher
um template é desperdício de latência e de dinheiro. Nos prompts do CP03/CP04/CP05,
que são justamente os de raciocínio, eu faria o oposto.

### Duas coisas que o ambiente ensinou

**O provider do Google não reporta custo.** O assert `cost` não falha — ele
**erra** a execução inteira com *"Cost assertion does not support providers that
do not return cost"*. Resolvi declarando o preço no provider (`inputCost` /
`outputCost`). Detalhe que custou tempo: a chave plana `cost:` é ignorada, só o
par `inputCost`/`outputCost` funciona, e em `gemini-3.7-flash` nem isso — devolve
zero de qualquer jeito. Acabei em `gemini-3.1-flash-lite`, que calcula
corretamente.

**Free tier do Gemini são 20 requisições por minuto.** Rodar os evals repetidamente
esgotou a cota e o promptfoo passou a enfileirar chamadas até estourar 300s de
timeout — sintoma que parece bug de config e não é. Rodei com `-j 2 --delay 2000`
a partir daí. Numa biblioteca com CI isso vira requisito: a suíte precisa de
conta paga ou de agendamento, senão o pipeline falha por cota e o time perde a
confiança no sinal.

### O frontmatter viaja junto com o prompt

Verifiquei uma dúvida que o formato do CP07 levanta: como `prompt.md` começa com
`---`, o promptfoo poderia interpretar o arquivo como **vários** prompts
separados por delimitador. Testei — não separa, detecta 1 prompt. Mas o
frontmatter YAML inteiro (`nome`, `versao`, `tags`, `inputs`) **é enviado ao
modelo** como parte do prompt.

Não quebrou nada e o custo é desprezível, mas não é o "texto puro do prompt" que
o template promete. A correção limpa é uma função de carregamento que remove o
frontmatter antes de enviar. Deixei como está para não divergir do esqueleto do
enunciado, que aponta `file://…/prompt.md` direto — mas fica anotado como dívida
do registry.

### Fronteira do determinístico

Os asserts deste checkpoint provam **forma e presença**: os cinco rótulos estão
lá, o handle casa `@\w+`, a nota cabe em 8 linhas, a política tem as portas
certas e nenhum `- {}`. Nenhum deles prova que a **hipótese está correta** ou que
a **causa provável faz sentido**.

O caso mais claro é a Entrada 3 da triagem-de-pods. O assert verifica que a saída
não contém `CrashLoopBackOff`, `OOMKilled`, `Pending`. Isso pega o modelo que
inventa problema em cluster saudável — que era o pior erro do CP01. Mas não pega
o modelo que diz "SAUDÁVEL" e escreve um parágrafo de bobagem logo abaixo: sem
palavra proibida, passa.

Essa é a fronteira, e é o que justifica a camada de julgamento do CP09.

---

## Como reproduzir

```bash
export OPENAI_API_KEY=...   # openai:gpt-4o-mini
export GOOGLE_API_KEY=...   # google:gemini-3.1-flash-lite

cd devops/nota-de-triagem
npx promptfoo@0.122.0 eval -c promptfooconfig.yaml --no-cache -j 2 --delay 2000
```

Requer Node ≥ 22.22. O `-j 2 --delay 2000` existe por causa do limite de 20
req/min do free tier do Gemini; com conta paga, rode sem eles.
