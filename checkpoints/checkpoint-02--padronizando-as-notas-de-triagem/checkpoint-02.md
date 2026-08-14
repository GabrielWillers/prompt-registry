# Checkpoint 02 — Padronizando as notas de triagem

## Decisão de método (e por que ela)

O enunciado deixa a escolha em aberto: dá pra ensinar o padrão de mais de uma
forma. As duas que considerei:

**Few-shot puro** — colar as três notas de referência e deixar o modelo inferir
a regra. Barato de escrever e pega bem o tom. O problema apareceu no primeiro
teste: os três exemplos do padrão são de Relay, Forge e Cerebro, e os três
alertas de entrada também. Quando o alerta de Relay chegou, a saída herdou
"deploy do Relay às 09:14" do exemplo de Relay — horário que não existe em lugar
nenhum na entrada. Few-shot com exemplos do mesmo domínio da entrada convida à
cópia de conteúdo, não só de forma.

**Especificação de schema** — descrever o contrato campo a campo, com as regras
de cada um. Sozinha, acerta a estrutura e erra a granularidade: o modelo produz
os cinco campos, mas escreve `IMPACTO: clientes afetados`, que é curto demais
pra ser útil, ou dois parágrafos, que é longo demais pra passagem de turno.

**Escolhi combinar as duas, com peso deliberado na especificação.** O schema
carrega a regra; os exemplos carregam só tom e granularidade, e vêm marcados
explicitamente como tal:

> Estes exemplos ilustram o padrão de qualidade esperado. Eles NÃO correspondem
> ao alerta que você vai processar agora — use-os só como referência de tom,
> granularidade e nível de especificidade de cada campo.

Essa marcação é o que separa "aprenda a forma daqui" de "copie o conteúdo
daqui". Depois dela, a contaminação sumiu nas três entradas.

Construção via meta-prompting em duas rodadas: gerei o primeiro prompt pedindo à
IA um gerador de notas a partir do padrão, e a segunda rodada foi crítica
adversarial — pedi que ela apontasse onde o próprio prompt permitiria inventar
dado. Foi daí que saíram as regras de "não invente números, tenants ou horários"
e de gatilho verificável em `ESCALAR PARA`.

---

## Prompt parametrizável

```
<papel>
Você é o assistente de triagem de plantão da Aegis, uma plataforma de observabilidade
composta por quatro sistemas: Relay (ingestão/barramento de eventos), Forge (pipeline
de dados e data warehouse), Sentinel (observabilidade e alerting) e Cerebro (indexação
e busca). Sua função é transformar um alerta bruto em uma nota de triagem padronizada,
pronta para o próximo plantonista assumir o turno sem precisar reler o alerta original.
</papel>

<formato_esperado>
A nota tem exatamente cinco campos, uma linha cada, sem markdown, sem numeração:

ALERTA: <sistema afetado> - <sintoma técnico observado, objetivo e mensurável>
IMPACTO: <quem/o que é afetado e em que magnitude ou escopo>
HIPÓTESE INICIAL: <causa mais provável, ancorada em evidência explícita do alerta bruto>
AÇÃO IMEDIATA: <ação concreta e executável, já em curso ou a ser tomada agora>
ESCALAR PARA: <time responsável> se <condição objetiva com limite numérico ou de tempo>

Regras:
- Cada campo é uma única frase curta e direta. Nada de explicações longas.
- HIPÓTESE INICIAL é uma hipótese, não uma certeza — não afirme causa que o alerta
  não sustenta; se a evidência for fraca, formule como hipótese mais provável mesmo assim.
- ESCALAR PARA sempre tem um gatilho verificável (tempo, percentual ou limiar), nunca
  "se piorar" de forma vaga.
- Não invente números, tenants ou horários que não estejam no alerta bruto.
- Não copie os exemplos de estilo literalmente; eles mostram tom e granularidade, não
  o conteúdo desta execução.
</formato_esperado>

<exemplos_de_estilo>
Estes exemplos ilustram o padrão de qualidade esperado. Eles NÃO correspondem ao alerta
que você vai processar agora — use-os só como referência de tom, granularidade e nível
de especificidade de cada campo.

ALERTA: Relay - taxa de rejeição de ingestão acima de 2% por 5min
IMPACTO: ingestão de telemetry degradada para ~12% dos tenants
HIPÓTESE INICIAL: deploy do Relay às 09:14 reduziu o buffer de ingestão
AÇÃO IMEDIATA: rollback iniciado via Argo CD
ESCALAR PARA: @relay-core se a rejeição não cair em 10min

ALERTA: Forge - lag de ingestão acima de 15min
IMPACTO: dashboards do Sentinel atrasados para todos os tenants
HIPÓTESE INICIAL: pico de volume do tenant acme-corp saturou o consumer
AÇÃO IMEDIATA: aumento manual de partições do consumer do Relay
ESCALAR PARA: @data-platform se lag não estabilizar em 20min

ALERTA: Cerebro - latência de busca p99 acima de 4s
IMPACTO: investigação de incidentes lenta para o time interno
HIPÓTESE INICIAL: reindexação noturna não concluiu antes do horário comercial
AÇÃO IMEDIATA: pausar reindexação e priorizar shard quente
ESCALAR PARA: @search-infra se p99 não cair em 15min
</exemplos_de_estilo>

<mapa_escalonamento>
{{MAPA_ESCALONAMENTO}}
</mapa_escalonamento>

Use o <mapa_escalonamento> para decidir o time em ESCALAR PARA. Se ele vier vazio,
use este default:
- Relay → @relay-core
- Forge → @data-platform
- Cerebro → @search-infra
- Sentinel → @sentinel-core

Se o sistema afetado não estiver no mapa em uso, escreva ESCALAR PARA: @oncall-plataforma
e sinalize entre colchetes, ao final da linha, que o time responsável não está mapeado.

<alerta_bruto>
{{ALERTA_BRUTO}}
</alerta_bruto>

<instrucao_final>
Antes de escrever, raciocine internamente (sem mostrar esse raciocínio no output) sobre:
qual sistema da Aegis é o afetado, qual o escopo real do impacto, qual a hipótese mais
sustentada pelas evidências do alerta bruto, qual ação imediata é plausível dado o tipo
de sistema, e qual gatilho objetivo de escalonamento faz sentido.

Depois, produza APENAS a nota de triagem no formato de <formato_esperado>, nada além
disso — sem preâmbulo, sem explicação, sem markdown.
</instrucao_final>
```

**Parâmetros.** `{{ALERTA_BRUTO}}` é o único obrigatório. `{{MAPA_ESCALONAMENTO}}`
é opcional e existe porque o mapa de times é a parte do prompt que muda de
organização para organização — deixá-lo fixo no corpo tornaria o item inútil
fora da Aegis.

---

## Execução — modelo: Claude Sonnet 5

**Por que este modelo, e não o Opus.** Downgrade deliberado. Aqui a tarefa é
preencher cinco campos a partir de um alerta curto: extração e formatação, não
raciocínio causal. É o item de **maior volume** da biblioteca — roda toda vez que
um alerta dispara, não uma vez por incidente —, então custo por token e latência
pesam de verdade, e a nota sai enquanto o plantonista ainda está lendo o alerta.
Rodei os três casos no Opus também: a saída foi equivalente, o que confirma que a
capacidade extra não estava sendo usada. Pagar por ela seria desperdício.

**Privacidade:** os alertas trazem nome de tenant (`stark-industries`,
`wakanda-systems`), que num cliente real é identificador comercial. É o dado mais
sensível deste checkpoint e o mais fácil de vazar, porque a nota é gerada dezenas
de vezes por dia e ninguém revisa cada uma. Em produção eu pseudonimizaria o
tenant antes do envio (`tenant-A`) e manteria o mapa fora do prompt — a nota não
precisa do nome real para ser útil ao plantonista, que já sabe qual cliente é
pelo ID do alerta.

Rodado com `{{MAPA_ESCALONAMENTO}}` vazio nas três entradas, ou seja, usando o
default embutido.

**Entrada 1:**
```
ALERTA: Sentinel - autoscaler no limite máximo de réplicas (60/60) em sentinel-api
IMPACTO: processamento de alerting sob pressão, fila de eventos do Relay crescendo ~2k/min
HIPÓTESE INICIAL: onboarding de nova região do tenant stark-industries elevou o volume a 4x a baseline, saturando a capacidade atual do Sentinel
AÇÃO IMEDIATA: elevar limite máximo de réplicas do autoscaler do sentinel-api e aplicar rate-limit temporário no tenant stark-industries
ESCALAR PARA: @sentinel-core se CPU permanecer acima de 85% ou a fila do Relay não estabilizar em 10min
```

**Entrada 2:**
```
ALERTA: Relay - taxa de rejeição de ingestão em 6% por 8min
IMPACTO: ingestão de telemetry degradada para o tenant wakanda-systems
HIPÓTESE INICIAL: deploy das 02:55 saturou o buffer de ingestão do Relay
AÇÃO IMEDIATA: rollback do deploy das 02:55 via Argo CD
ESCALAR PARA: @relay-core se a rejeição não cair abaixo de 6% em 10min
```

**Entrada 3:**
```
ALERTA: Forge - lag do consumer em 9min e subindo
IMPACTO: dashboards e alerting do Sentinel começando a atrasar para os tenants dependentes do batch forge-batch-ingest
HIPÓTESE INICIAL: falha do job anterior atrasou o batch forge-batch-ingest, causando acúmulo de lag no consumer
AÇÃO IMEDIATA: reprocessar/reiniciar o batch forge-batch-ingest e monitorar acúmulo do consumer
ESCALAR PARA: @data-platform se o lag não estabilizar em 20min
```

---

## Curadoria

**A contaminação por few-shot foi o achado principal.** Vale registrar porque é
contra-intuitivo: os exemplos que melhoram a saída são os mesmos que a
envenenam, e o ponto de virada é o quanto o domínio dos exemplos se parece com o
domínio da entrada. Aqui era idêntico. A saída da Entrada 2 é a prova de que a
correção pegou: o alerta cru diz `deploy 02:55`, e a nota diz `deploy das 02:55`
— não os `09:14` do exemplo de Relay que estava logo acima no prompt.

**Um defeito meu que só apareceu relendo o prompt.** A primeira versão dizia
"se `{{MAPA_ESCALONAMENTO}}` for fornecido, ele substitui o default" e
interpolava o placeholder *logo abaixo da lista default, dentro da mesma tag*.
Com um mapa preenchido, o modelo receberia as duas listas coladas e nenhuma
forma de saber qual manda — "substitui" é instrução pra quem monta o prompt, não
pro modelo, que só vê o texto final. Separei: o placeholder ficou sozinho na
tag, e o default virou instrução condicional fora dela. As três execuções
rodaram com mapa vazio, então não expuseram o bug — é o tipo de coisa que só
quebra no primeiro time que tentar reusar o item, que é exatamente quem uma
biblioteca deveria proteger.

**Fallback para sistema fora do mapa.** Na primeira versão eu tinha registrado
isso como limitação conhecida e deixado pra lá. Limitação que tem conserto de
duas linhas não é limitação, é pendência: alerta de sistema não mapeado agora
cai em `@oncall-plataforma` com sinalização explícita, em vez de o modelo
escolher um time por conta.

**O que a regra de frase curta comprou.** Sem ela, o `IMPACTO` inflava com
adjetivo vago ("degradação significativa", "impacto considerável"). O campo tem
uma função na passagem de turno: dizer o escopo. "Significativo" não é escopo.
Comparar `~12% dos tenants` com "impacto considerável" mostra o tamanho da
diferença.

**Limite que fica.** A `AÇÃO IMEDIATA` é plausível, não verificada — o modelo
não sabe o que o time tem de fato automatizado. Na Entrada 1 ele sugeriu
rate-limit por tenant, que é uma ação razoável e pode simplesmente não existir
na plataforma. A nota é ponto de partida para o plantonista, não ordem de
execução.
