# Checkpoint 09 — Gate de qualidade com LLM-as-judge

O CP08 cobriu o que se checa sem opinião: formato, latência, custo. A análise de
causa-raiz do CP03 não cabe ali — não há regex que decida se um diagnóstico está
certo. Este checkpoint põe um gate de julgamento em cima da camada determinística.

O config vive em [`devops/causa-raiz/promptfooconfig.yaml`](../../devops/causa-raiz/promptfooconfig.yaml),
ao lado do `prompt.md`, seguindo a mesma convenção do CP08.

**Ambiente:** promptfoo 0.122.0, Node 22.23.2.
**Modelos avaliados:** `openai:gpt-4o-mini` e `google:gemini-3.1-flash-lite`, temperatura 0.
**Juiz:** `openai:gpt-4o`, temperatura 0 — modelo diferente e mais capaz que os avaliados.

---

## 1. A rubrica

Quatro critérios, escala 0–2 (0 = não atende, 1 = parcial, 2 = atende), total 0–8.

| # | Critério | O que mede |
|---|---|---|
| 1 | **causa_raiz** | Aponta a causa real — a reindexação travada saturando o heap, levando a circuit breaker, timeouts de busca e queda do cache — e não apenas os sintomas |
| 2 | **correlacao_causa** | Separa o que é causa do que é consequência (o cache hit caindo é efeito, não causa) |
| 3 | **acao_proporcional** | Ação coerente com o diagnóstico, sem sobre nem subdimensionar |
| 4 | **honestidade_epistemica** | Reconhece o que os dados não permitem concluir, em vez de fabricar certeza |

**Critério de aprovação: total ≥ 6 E nenhum critério zerado.**

O que fez a rubrica funcionar não foram os quatro enunciados — foram as **âncoras
por nota**. Cada critério define o que é 0, o que é 1 e o que é 2, em termos
observáveis. Sem elas o juiz pontua por impressão geral e a nota vira ruído:

```
1. causa_raiz
   0 = aponta só sintomas, ou aponta uma causa errada (culpa o cache, o volume
       de busca, ou trata heap pequeno como gatilho);
   1 = chega ao mecanismo (heap esgotado / circuit breaker) mas NÃO identifica
       a reindexação fora de janela como origem;
   2 = identifica a reindexação atrasada como gatilho E a cadeia até os sintomas.
```

O prompt do juiz também carrega a **verdade de referência** do incidente — a causa
real, as relações de causa que importam e as lacunas conhecidas dos dados. Sem
isso o juiz não tem contra o que comparar e passa a premiar prosa bem escrita.

---

## 2. O gate — e por que ele são DOIS asserts

```yaml
assert:
  # (1) nota total no corte
  - type: llm-rubric
    threshold: 0.75 # 6/8
    value: |
      Pontue os quatro critérios, some o total (0 a 8) e devolva:
      - score = total / 8, SEMPRE, sem exceção e sem nenhuma outra condição;
      - pass = (total >= 6).
      Não aplique nenhuma regra sobre critérios zerados nesta chamada.

  # (2) nenhum critério zerado
  - type: llm-rubric
    threshold: 1
    value: |
      Pontue os quatro critérios e responda APENAS a esta pergunta:
      algum dos quatro recebeu nota 0?
      - Se SIM  -> score = 0, pass = false.
      - Se NÃO  -> score = 1, pass = true.
```

Mais a rede de segurança operacional herdada do CP08 — `cost` em US$ 0,05 e
`latency` em 90s, limiares folgados de propósito, porque o CP08 mostrou que um
teto de 5s mede tamanho de saída e esta é a saída mais longa da biblioteca.

A separação em dois asserts não é estética. É a correção de um furo real,
descrito na curadoria abaixo.

---

## 3. Calibração

Escrevi oito saídas candidatas, pontuei cada uma à mão **antes** de rodar o juiz,
e comparei. Meta: no máximo 1 ponto de diferença em cada critério.

| Fixture | O que é | Minha nota | Total | Esperado |
|---|---|---|---|---|
| A | análise excelente (a do CP03) | 2/2/2/2 | 8 | PASS |
| B | só sintoma — culpa o heap, ignora o reindex | 1/0/1/0 | 2 | FAIL |
| C | causalidade invertida — culpa o cache | 0/0/1/0 | 1 | FAIL |
| D | causa certa, mas arrogante e ação desproporcional | 2/2/0/0 | 4 | FAIL |
| E | **limítrofe** — exatamente no corte | 2/1/2/1 | 6 | PASS |
| F | prolixo e vazio — muito texto, zero análise | 0/0/0/0 | 0 | FAIL |
| G | **uniforme medíocre** — saída real reprovada do gpt-4o-mini | 1/1/1/1 | 4 | FAIL |
| H | **seis com zero** — atinge o corte mas zera um critério | 2/2/2/0 | 6 | FAIL |

As três últimas nasceram de falhas encontradas durante a calibração, não de
planejamento — cada uma é um caso que o juiz errou antes de eu apertar a rubrica.

### Resultado final

```
fix  humano     juiz        Δ  h.t  j.t    A1    A2   gate  esper
------------------------------------------------------------------
A    2/2/2/2    2/2/2/2     0    8    8  PASS  PASS   PASS   PASS
B    1/0/1/0    0/0/0/0     1    2    0  FAIL  FAIL   FAIL   FAIL
C    0/0/1/0    0/0/0/0     1    1    0  FAIL  FAIL   FAIL   FAIL
D    2/2/0/0    2/2/0/0     0    4    4  FAIL  FAIL   FAIL   FAIL
E    2/1/2/1    2/1/2/1     0    6    6  PASS  PASS   PASS   PASS
F    0/0/0/0    0/0/0/0     0    0    0  FAIL  FAIL   FAIL   FAIL
G    1/1/1/1    1/1/1/1     0    4    4  FAIL  PASS   FAIL   FAIL
H    2/2/2/0    2/2/2/0     0    6    6  PASS  FAIL   FAIL   FAIL

Δ máximo por critério: 1 (meta <=1)   vereditos errados: 0/8
```

**Δ máximo 1 em todos os critérios, 6 de 8 fixtures com Δ zero, e 0 vereditos
errados.** Reproduzido em duas rodadas seguidas com resultado idêntico.

As linhas G e H mostram o gate funcionando por dois caminhos diferentes: em G o
assert 1 reprova (total 4) e o 2 aprova (nenhum zero); em H é o inverso — o
assert 1 aprova (total 6) e o 2 reprova. Os dois asserts juntos dizem *por que*
reprovou, o que um assert único não daria.

Saída completa em [`saida-calibracao.txt`](./saida-calibracao.txt).

---

## 4. Execução do gate em produção

```
========================================================================
provider: openai:gpt-4o-mini   GATE: FAIL   13937ms  $0.00071
  [FALHA] llm-rubric  score=0.625
     causa_raiz=1; correlacao_causa=2; acao_proporcional=1;
     honestidade_epistemica=1; total=5. A análise identifica o mecanismo (heap
     esgotado) mas não a reindexação fora da janela como origem. A ação proposta
     ataca o mecanismo, mas não aborda a reindexação. Reconhece lacunas, mas não
     gradua a confiança na conclusão.
  [ok   ] llm-rubric  score=1     (nenhum critério zerado)
  [ok   ] cost        score=1
  [ok   ] latency     score=1

========================================================================
provider: google:gemini-3.1-flash-lite   GATE: PASS   10792ms  $0.00075
  [ok   ] llm-rubric  score=1
     causa_raiz=2; correlacao_causa=2; acao_proporcional=2;
     honestidade_epistemica=2; total=8. Identifica corretamente a reindexação
     fora da janela como gatilho e a cadeia até os sintomas. Distingue causa de
     consequência, propõe ações proporcionais e gradua a confiança.
  [ok   ] llm-rubric  score=1     (nenhum critério zerado)
```

Veredito e justificativas do juiz em [`saida-gate-producao.txt`](./saida-gate-producao.txt).
As **análises de causa-raiz integrais** que o juiz pontuou estão em
[`saidas-dos-modelos.md`](./saidas-dos-modelos.md).

O gate está fazendo exatamente o trabalho para o qual existe: **reprovou uma
saída que a camada determinística do CP08 aprovaria sem hesitar.** A resposta do
`gpt-4o-mini` tem as nove seções do formato, cita métricas e logs, cabe no custo
e na latência. Nenhum regex a barraria. Ela só não chega à causa-raiz.

---

## 5. Curadoria

### O furo que só apareceu porque eu fui procurar

Depois de a calibração fechar em Δ ≤ 1 com seis fixtures, tudo parecia pronto.
Faltava testar o caso exato para o qual a regra "nenhum critério zerado" existe:
uma análise que **atinge o corte e mesmo assim deve reprovar**. Escrevi a fixture
H — causa-raiz certa, separação impecável, ação proporcional, e uma conclusão
que afirma *"o diagnóstico está fechado e não há margem para dúvida"*. Ou seja,
2/2/2/0 = 6.

O gate **aprovou**. O juiz devolveu `score: 0.75` e `pass: true`, tendo pontuado
`honestidade_epistemica=0` no próprio texto da justificativa. A regra estava
escrita na rubrica e o juiz simplesmente não a aplicou.

Se eu tivesse parado na calibração "bem-sucedida", teria entregue um gate que
aprova análises arrogantes — justamente a falha mais perigosa num playbook de
plantão, porque uma conclusão errada dita com convicção é o que faz o time agir
na direção errada.

**Lição:** calibrar contra saídas típicas não é suficiente. É preciso construir
o caso adversarial que ataca a regra específica do gate, e é ele que revela se a
regra é real ou decorativa.

### Por que dois asserts, e não um juiz mais bem instruído

Antes de reestruturar, tentei três rodadas de ajuste no prompt para o juiz
aplicar a regra composta. Foi um jogo de empurra:

1. Instrução em prosa (`se zerado, score = 0.0`) → o juiz devolvia 0.0 para
   *qualquer* reprovação, inclusive 1/1/1/1, o que destrói a leitura da nota.
2. Adicionei um exemplo enfático de que 1/1/1/1 deve dar 0.5 → consertou esse
   caso e **quebrou o oposto**: 2/2/0/0 passou a devolver 0.5 em vez de 0.0.
3. Troquei a prosa por uma tabela de consulta com a linha do zero em primeiro
   lugar → consertou 1/1/1/1, e 2/2/0/0 continuou errado.
4. Adicionei exemplo trabalhado com as notas exatas de 2/2/0/0 → sem efeito.

O padrão é claro: **o juiz pontua os critérios muito bem e calcula regras
compostas muito mal.** Nas oito fixtures ele errou zero notas de critério e
errou sistematicamente a aritmética condicional em cima delas.

A correção não é instruir melhor — é parar de pedir. Cada assert passou a ter
uma pergunta trivial ("qual o total?" / "algum critério é zero?") e o **promptfoo
faz o E entre eles**. A lógica composta saiu do LLM e foi para o test runner, que
é determinístico por construção. Depois disso, 8 de 8 vereditos corretos, duas
rodadas seguidas.

Custa uma chamada de juiz a mais por saída avaliada — US$ 0,0007 no total.
Barato pelo que compra.

### O que a calibração corrigiu na rubrica

**Âncora de honestidade epistêmica.** Na primeira rodada, a fixture E (limítrofe)
recebeu 2 do juiz e 1 meu. E cita a lacuna de 02:00–08:00 mas nunca gradua a
confiança da conclusão. Como E está exatamente no corte, essa generosidade
significava que um candidato de 5 pontos reais viraria 6 e passaria. Apertei:

> 1 = cita ao menos uma lacuna real mas **NÃO** gradua a confiança. Citar uma
> lacuna e parar aí é 1, nunca 2 — por mais bem escrita que seja a citação.

Na rodada seguinte E caiu para 2/1/2/1, batendo comigo ponto a ponto.

**Fixture contra prolixidade.** Escrevi F — quatro parágrafos que recitam as
métricas, elogiam a complexidade do Elasticsearch e não concluem nada — para
testar se o juiz confunde volume com qualidade. Não confundiu: 0/0/0/0. Mas era
um risco real que valia medir, e a regra `Texto longo não é melhor por ser longo`
ficou na rubrica.

### As duas divergências que sobraram, e por que aceitei

Em B e C o juiz é mais duro que eu em `acao_proporcional`: dei 1, ele dá 0.

Em B a ação é "aumentar o heap para 16g"; eu li como plausível-mas-insuficiente
(minha âncora de 1: *"ataca principalmente o mecanismo"*). O juiz argumenta que
B também propõe aumentar o query cache, o que sob pressão de heap **piora** a
situação — logo, incoerente com o próprio diagnóstico, que é a definição do 0.
Ele tem razão e eu fui generoso.

Deixei a divergência em vez de reescrever a âncora para forçar a concordância.
Δ = 1 é o alvo declarado, os dois vereditos batem, e ajustar a rubrica até o
juiz concordar comigo em tudo é overfitting ao meu próprio viés — não calibração.

### O gate pega variância que eu não esperava

Rodando o gate quatro vezes contra o mesmo pacote de artefatos, o `gpt-4o-mini`
tirou **4, 6, 6 e 5**. Ou seja: passava ou reprovava conforme a rodada. Fixei
`temperature: 0` também nos geradores — e continuou oscilando entre 5 e 6, porque
a API não é determinística mesmo em temperatura zero.

Mas há um sinal estável no meio do ruído: **`causa_raiz = 1` nas quatro rodadas,
sem exceção.** O gpt-4o-mini nunca identifica que a reindexação furou a janela.
O que oscila são os critérios mais moles. O total gira em torno do corte porque
o modelo é genuinamente limítrofe para esta tarefa — e é isso que o gate está
reportando.

Duas recomendações que saem daí, e que ficam registradas para o CP10 sem alterar
a regra fixada no enunciado:

1. **Um modelo no limite produz gate intermitente.** Para o pipeline, ou se usa
   um modelo que passa com folga (o Gemini deu 8/8 em todas as rodadas), ou se
   aceita rodar N vezes e usar a mediana.
2. **`causa_raiz` deveria ser sub-gate obrigatório em 2.** É o critério que
   define se a análise serve para alguma coisa, e é o mais estável dos quatro.
   Um total 6 construído com `causa_raiz=1` aprova uma análise que não achou a
   causa — tecnicamente dentro da regra, praticamente inútil.

### O que este gate não pega

O juiz conhece a resposta certa: a verdade de referência está escrita no prompt
dele. Isso torna o gate confiável **para este incidente** e inútil para qualquer
outro. Um pacote de artefatos novo exige uma nova verdade de referência escrita à
mão, e portanto uma nova calibração.

Ou seja: o que está versionado aqui é um **teste de regressão do prompt**, não um
avaliador genérico de causa-raiz. Ele responde "o prompt piorou depois desta
mudança?" — que é exatamente a pergunta do CP10 — e não responde "esta análise
está certa?" para um incidente qualquer.

---

## Como reproduzir

```bash
export OPENAI_API_KEY=...   # geradores + juiz
export GOOGLE_API_KEY=...   # gerador gemini

# gate de produção
cd devops/causa-raiz
npx promptfoo@0.122.0 eval -c promptfooconfig.yaml --no-cache -j 1 --delay 3000

# calibração do juiz contra a pontuação humana
cd checkpoints/checkpoint-09-gate-de-qualidade-llm-as-judge/calibracao
npx promptfoo@0.122.0 eval -c promptfooconfig.yaml --no-cache -j 2
```

A pasta `calibracao/` contém as oito fixtures e o config com provider `echo` —
a saída avaliada é o texto da fixture, o que permite comparar juiz e humano sobre
o mesmo material.
