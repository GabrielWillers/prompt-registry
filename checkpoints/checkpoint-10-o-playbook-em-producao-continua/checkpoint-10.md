# Checkpoint 10 — O playbook em produção contínua

O que faltava para o repositório virar sistema: garantir que nenhuma alteração
entre sem passar pelos testes. Este checkpoint leva a cobertura aos 8 prompts e
monta o pipeline que roda a suíte a cada mudança.

- **Workflow:** [`.github/workflows/playbook.yml`](../../.github/workflows/playbook.yml)
- **Validador de convenções:** [`tools/validar-convencoes.py`](../../tools/validar-convencoes.py)
- **Evidência de execução:** [`evidencia-execucao.md`](./evidencia-execucao.md)
- **PR de regressão (mantido aberto):** [#1](https://github.com/GabrielWillers/prompt-registry/pull/1)

---

## 1. Cobertura: de 4 para 8 prompts

O CP08 cobriu 3 prompts de saída estruturada e o CP09 pôs o juiz em 1. Faltavam
os 4 de saída aberta — a decisão de arquitetura e os três elos da cadeia de
migração. Todos ganharam suíte **híbrida**:

| Prompt | Tier 1 (determinístico) | Tier 2 (juiz) |
|---|---|---|
| nota-de-triagem | 5 rótulos, handle `@\w+`, ≤ 8 linhas | — |
| triagem-de-pods | pods citados, causa, caso saudável | — |
| networkpolicy-sentinel | `kind`, portas, sem `- {}`, labels do mapa | — |
| causa-raiz | — | rubrica 0–8, corte ≥ 6 |
| decisao-de-arquitetura-com-tradeoffs | 6 seções, tabela com ≥ 3 opções, duras × brandas | gargalo, restrições, alternativas, sacrifício |
| diagnostico-de-acoplamento (elo 1) | 4 seções nomeadas, `I1..In`, tabela de riscos, **não propõe plano** | cadência, invariantes, falha silenciosa |
| plano-faseado (elo 2) | mermaid, cita `I*`, parallel-run antes do corte, critério com número | ordem de risco, parallel-run isolado |
| runbook-de-fase (elo 3) | 5 seções, execução numerada, **abort com número**, uma fase só | abort objetivo, portões por invariante |

A parte determinística dos 4 novos não foi inventada agora: são os *testes
estruturais* que eu já tinha escrito como checklist no CP05. Ali eles eram uma
promessa; aqui viraram asserts executáveis. É a diferença entre documentar um
contrato e verificá-lo.

**O contrato de handoff da cadeia é o caso mais forte.** O elo 2 consome a saída
do elo 1 sem edição. Se o elo 1 parar de numerar as invariantes ou renomear uma
seção, a cadeia quebra **silenciosamente** — o elo 2 recebe um texto que não
casa e produz um plano que não protege nada. Nenhum humano revisando o PR do elo
1 perceberia. O assert percebe.

---

## 2. A estratégia de gate

Três camadas, com autoridade decrescente sobre o build:

```
CAMADA 0  convenções          bloqueia   ~10s     US$ 0      sem chamar modelo
CAMADA 1  asserts estruturais bloqueia   ~30s     US$ ~0,001 por prompt
CAMADA 2  LLM-as-judge        bloqueia   ~40s     US$ ~0,013 por prompt
CAMADA 3  compat. de modelo   informa    ~3min    US$ ~0,08  não derruba build
```

**Falha o build:** qualquer assert reprovado — estrutural ou de juiz — que
persista após **uma** reexecução automática.

**Não falha o build:** o job de compatibilidade com o modelo secundário, e uma
falha que desapareça na segunda tentativa (registrada como aviso).

A camada 0 existe porque ela é grátis e pega o defeito que já quebrou este
repositório de verdade: no CP07, `descricao: Sistema sob análise (ex.: Cerebro)`
era YAML inválido e o GitHub não renderizava o frontmatter. Estava em 8 arquivos.
Não faz sentido pagar avaliação de modelo para um prompt cujo metadado nem
parseia — e ela também verifica que `inputs` bate com os `{{placeholders}}` nos
dois sentidos, que é o contrato que o CP07 estabeleceu.

---

## 3. Evidência

### Build verde — push na `main`

Os 8 prompts, mais as três camadas:

```
success  Convenções do catálogo          success  devops/causa-raiz
success  Definir escopo                  success  devops/triagem-de-pods
success  devops/nota-de-triagem          success  devops/networkpolicy-sentinel
success  devops/decisao-de-arquitetura…  success  devops/diagnostico-de-acoplamento…
success  devops/plano-faseado…           success  devops/runbook-de-fase…
success  Compatibilidade (informativo)
```

### Build vermelho — PR com prompt regredido

Abri o [PR #1](https://github.com/GabrielWillers/prompt-registry/pull/1) com uma
mudança que um time faria de boa-fé: *"a saída está longa demais para colar no
chat do plantão, vamos limitar"*. Adicionei um teto de linhas em `causa-raiz` e
em `runbook-de-fase-de-migracao`, e removi a exigência de critério de abort
objetivo.

```
success  Convenções do catálogo
success  Definir escopo
success  devops/causa-raiz
failure  devops/runbook-de-fase-de-migracao     <-- gate barrou
```

No log do job:

```
[FAIL] ## Pré-checagens
  0 passed (0%)   ✗ 1 failed (100%)
##[error] Evaluation success rate (0.00%) is below the required threshold (100%)
# retry automático:
  0 passed (0%)   ✗ 1 failed (100%)
##[error] Evaluation success rate (0.00%) is below the required threshold (100%)
```

Duas tentativas, duas falhas → build vermelho. Fosse instabilidade de provedor, a
segunda teria passado e o build seguiria verde com um aviso.

### A primeira regressão que tentei passou pelo gate

Vale mais registrar isto do que só o vermelho fácil. Minha primeira tentativa foi
**remover instruções**: tirei do `causa-raiz` os passos que mandam apontar
lacunas e graduar confiança, e do `runbook` a exigência de abort objetivo. O
build ficou **verde**.

Motivo: o modelo continuou fazendo aquilo mesmo sem a instrução. Remover uma
instrução não degrada a saída quando o comportamento já é o default do modelo.

Isso mede a **sensibilidade real** do gate, e a conclusão é desconfortável mas
honesta: ele detecta regressão que muda a **saída**, não regressão que enfraquece
o **prompt**. Um prompt pode ficar mais frágil — dependendo de sorte do modelo em
vez de instrução explícita — sem que nenhum assert perceba, até o dia em que
troca o modelo e tudo desaba de uma vez. O gate protege contra regressão
observável; contra erosão de robustez, não protege.

---

## 4. Justificativa das decisões de design

### 4.1 O que exatamente derruba o build

**Escolhido: determinístico + juiz, ambos bloqueantes, com um retry.**

| Alternativa | Ganha | Perde |
|---|---|---|
| **Só asserts determinísticos** | Zero flutuação, build sempre confiável, custo baixíssimo | Não pega nada do que importa nos 5 prompts de saída aberta. O CP09 mostrou o caso: o `gpt-4o-mini` produziu uma causa-raiz com as 9 seções, métricas citadas e custo dentro do teto — passaria em todo assert estrutural — e não achou a causa |
| **Juiz apenas informativo** | Nunca reprova build por flutuação; time vê a nota sem atrito | Nota que não bloqueia é ignorada. O objetivo do checkpoint é "barrar regressão", e um aviso não barra nada |
| **Ambos bloqueantes (escolhido)** | O gate cobre forma e substância | Expõe o build à variância do juiz — mitigada abaixo |

O argumento decisivo veio do CP09: a saída que o gate reprovou tinha **todas as
seções e todos os números certos**. Um gate só determinístico teria aprovado uma
análise que não encontra a causa-raiz. Isso não é gate, é verificação de formato.

### 4.2 Flutuação do juiz

**Escolhido: temperatura 0 nos dois lados + uma reexecução automática.**

Esta decisão se apoia em medição, não em intuição. Na calibração do CP09 rodei o
juiz **cinco vezes** sobre as mesmas oito fixtures, em temperatura 0: as notas
saíram **idênticas nas cinco**. O juiz não é a fonte da flutuação. Quem varia é o
**gerador**: o `gpt-4o-mini` produziu 4, 6, 6 e 5 sobre o mesmo pacote de
artefatos.

| Alternativa | Ganha | Perde |
|---|---|---|
| **Rodada única, sem retry** | Mais barato, veredito imediato | Um 503 de provedor derruba o PR. Medi três 503 do Gemini e uma chamada de 194s onde a mediana é 13s. O time aprende a reexecutar sem ler, e o gate perde autoridade |
| **`--repeat 3` + mediana** | Absorve flutuação de forma estatística | **Triplica o custo em toda execução**, inclusive nas que iam passar de primeira. Paga o seguro em 100% dos casos para cobrir os ~5% que flutuam |
| **Retry uma vez (escolhido)** | Custo extra só quando falha; distingue transitório de real | Um prompt que falha 50% das vezes passa em ~75% das execuções. Mitigo com o aviso de instabilidade: duas ocorrências viram investigação |

O `::warning` de suíte instável é a peça que fecha isso. Sem ele, "passou no
retry" vira invisível e o gate degrada em silêncio.

**O que eu descartei e por quê:** cogitei baixar o corte do juiz de 6 para 5 para
dar folga. Rejeitei — isso não reduz flutuação, só move a linha. Um prompt que
oscila em torno de 6 vai oscilar em torno de 5 igual, e agora com a barra mais
baixa. Flutuação se combate na reprodutibilidade da medição, não afrouxando o
critério.

### 4.3 Suíte inteira ou só o que mudou

**Escolhido: híbrido por gatilho.**

| Gatilho | Escopo | Por quê |
|---|---|---|
| Pull request | Só os prompts alterados | Feedback em ~1min e custo proporcional à mudança |
| Push na `main` | Suíte completa | Rede que pega o que o escopo reduzido deixou passar |
| Cron semanal | Suíte completa | Provedor muda sem ninguém tocar no repositório |

| Alternativa | Ganha | Perde |
|---|---|---|
| **Sempre a suíte inteira** | Nunca deixa regressão passar por recorte errado | ~8× o custo e o tempo por PR. Num PR que mexe num prompt, 7/8 da execução é desperdício — e CI lento é CI que o time contorna |
| **Só alterados, sempre** | Mais barato e rápido possível | Não pega efeito colateral. E o `main` fica sem nenhuma verificação completa |
| **Híbrido (escolhido)** | Custo do PR proporcional; a completa roda onde é barata (fora do caminho crítico) | Uma regressão de efeito colateral só aparece no merge, não no PR |

Há uma exceção no cálculo do escopo que vale apontar: se o PR toca `tools/` ou o
próprio workflow, o escopo reduzido **esconderia** o efeito, então o pipeline
força a suíte completa. Mudança transversal exige verificação transversal.

### 4.4 Um provider de referência ou todos

**Escolhido: um provider de referência decide; o segundo informa.**

Esta foi a decisão mais difícil, porque tenho dados dos dois lados. O
`gpt-4o-mini` **reprova** em dois prompts hoje: tira 5/8 na causa-raiz (nunca
identifica que a reindexação furou a janela) e escreve uma fase com critério de
saída sem número, contrariando o texto do prompt.

| Alternativa | Ganha | Perde |
|---|---|---|
| **Todos os modelos bloqueiam** | O prompt tem de ser robusto em qualquer modelo — garantia mais forte | O `main` nasce **vermelho**, e build permanentemente vermelho não é gate, é ruído. Além disso, confunde duas perguntas diferentes |
| **Só o de referência (escolhido)** | Verde significa "o prompt funciona no modelo que o time roda" | Não protege quem usa outro modelo |
| **Nenhum bloqueia, matriz informativa** | Zero atrito | Zero garantia |

O que separa as opções é reconhecer que **"o prompt regrediu?" e "este modelo
aguenta o prompt?" são perguntas distintas, com consequências distintas.** A
primeira deve bloquear o merge; a segunda deve abrir um chamado. Misturá-las faz
com que uma regressão de modelo secundário bloqueie um PR de documentação.

Por isso os configs declaram um provider de referência e o job
`matriz-de-modelos` roda o secundário com `continue-on-error`, publicando uma
tabela de compatibilidade no resumo da execução.

### 4.5 Latência e custo como gate

**Escolhido: teto grosseiro, não limite fino.**

O CP08 fixou latência em 5s por enunciado, e eu já tinha medido ali que esse teto
mede **tamanho de saída**, não qualidade. Em CI o efeito foi pior: na primeira
execução da suíte completa, **4 dos 8 prompts reprovaram só por latência** —
7.378ms, 6.943ms, 5.105ms contra um teto de 5.000ms.

| Alternativa | Ganha | Perde |
|---|---|---|
| **Manter 5s bloqueante** | Pressão real por saída enxuta | Metade da suíte vermelha por causa da rede. O gate vira loteria e o time deixa de ler o resultado |
| **Tirar latência e custo** | Zero ruído | Perde a rede contra alguém fazer o prompt gerar 10× mais texto |
| **Teto grosseiro, 60s (escolhido)** | Continua pegando explosão de tamanho; para de pegar rede | Não pressiona por otimização fina de latência |

Um prompt não regride porque a chamada levou 7s em vez de 4s. O que interessa ao
gate é a mudança de ordem de grandeza — e para isso 60s serve melhor que 5s.

### 4.6 Custo por PR

Números medidos, não estimados de catálogo:

| Item | Custo |
|---|---|
| Geração (gemini-3.1-flash-lite, 1 caso) | ~US$ 0,0008 |
| Juiz (gpt-4o, 2 chamadas, ~4.400 tokens) | ~US$ 0,013 |
| **PR que mexe em 1 prompt com juiz** | **~US$ 0,014** |
| **Suíte completa (8 prompts, 5 com juiz)** | **~US$ 0,075** |
| **Mês típico** (20 PRs + 20 merges + 4 crons) | **~US$ 2,10** |

O juiz é **94% do custo**. As alavancas, em ordem de eficácia:

1. **Escopo por PR** — o que mais economiza; já implementado.
2. **Cache do promptfoo entre execuções** — chave por hash do `prompt.md`, então
   PR que não muda o prompt reaproveita a saída. Implementado com `actions/cache`.
3. **Um juiz mais barato** — descartado. O juiz é o instrumento de medição; se
   ele erra, o gate inteiro perde sentido. Economizar US$ 0,01 por PR
   comprometendo a medição é a pior troca disponível aqui.
4. **`max-parallel: 2` e `max-concurrency: 1`** — não economizam dinheiro, mas
   respeitam o rate limit de 20 req/min do free tier do Gemini, que já me deu
   429 e vários 503 durante o desenvolvimento.

Vale dizer com todas as letras: **o free tier não é infraestrutura de CI.** Os
503 que apareceram nos testes locais vão aparecer no pipeline, e é o retry que os
absorve. Numa operação real, o gate justifica conta paga.

### 4.7 Onde ficam as chaves

**Escolhido: secrets do repositório.**

| Alternativa | Ganha | Perde |
|---|---|---|
| **Secrets de repositório (escolhido)** | Simples; funciona em PR do mesmo repo; nunca aparece no log (o Actions mascara) | Qualquer um com write no repo consegue exfiltrar via workflow malicioso |
| **Environment secrets com aprovação** | Exige aprovação humana antes de expor a chave | Trava o feedback do PR atrás de revisor — mata o valor do gate automático |
| **OIDC / cofre externo** | Sem segredo de longa duração no GitHub | Nem OpenAI nem Google AI Studio suportam OIDC do GitHub hoje. Exigiria um proxy — infraestrutura desproporcional para este repositório |

Uma limitação estrutural que preciso registrar: **PR vindo de fork não recebe
secrets.** É proteção do GitHub, e correta. Consequência prática: contribuição
externa não roda a suíte automaticamente. As saídas seriam `pull_request_target`
(que executa código não confiável **com** os secrets — inaceitável) ou um mantenedor
reexecutar o pipeline a partir de um branch interno. Escolhi a segunda: o gate
não roda sozinho em PR de fork, e isso está documentado em vez de contornado com
uma brecha de segurança.

Chaves de provedor são credenciais pagas com raio de alcance grande. Uma
recomendação operacional que fica: use uma chave dedicada ao CI, com limite de
gasto próprio, para que vazamento vire prejuízo limitado e detectável.

---

## 5. O que fica em aberto

**Nenhuma suíte compara com a versão anterior.** O enunciado define regressão como
"uma mudança piora um prompt em relação à versão anterior", e o que este gate
mede é conformidade com um limiar absoluto, não delta. Um prompt que caía 8/8 e
passa a 6/8 continua verde. O caminho seria guardar a nota do `main` como baseline
e reprovar queda além de uma margem — a `promptfoo-action` tem infraestrutura de
comparação de PR que serviria de base.

**O sub-gate de `causa_raiz`.** No CP09 registrei que o critério de causa-raiz
deveria ser obrigatório em 2: um total 6 construído com `causa_raiz=1` aprova uma
análise que não achou a causa. Não implementei porque alteraria a regra fixada no
CP09; fica como a primeira mudança que eu faria.

**Três dos quatro juízes novos não estão calibrados.** Só o de `causa-raiz` passou
pelo processo do CP09 — oito fixtures pontuadas à mão, Δ ≤ 1 em cada critério. Os
juízes de decisão, diagnóstico, plano e runbook usam o mesmo formato e a mesma
estrutura de dois asserts, mas nunca foram confrontados com pontuação humana.
Estão bloqueando o build sem essa validação, o que é uma dívida real: um juiz
não calibrado pode estar generoso demais (não pega nada) ou duro demais (barra PR
legítimo). A calibração de cada um é trabalho de meia hora e é o que eu faria
antes de considerar este pipeline confiável em produção.
