---
nome: Nota de triagem de alerta
descricao: Converte um alerta bruto de monitoramento na nota de triagem padronizada de cinco campos usada na passagem de turno.
versao: 1.0.0
tags: [sre, plantao, alerting, padronizacao, incidentes]
inputs:
  - nome: alerta_bruto
    descricao: Texto cru do alerta como saiu do sistema de monitoramento, com horário, sistema e métricas.
  - nome: mapa_escalonamento
    descricao: Mapa de sistema para time responsável pelo escalonamento. Deixe vazio para usar o default embutido no prompt.
  - nome: contexto_plataforma
    descricao: Descrição curta dos sistemas da plataforma e do que cada um faz, para o modelo identificar o sistema afetado.
---

# Nota de triagem de alerta

## Objetivo

Acabar com a variação de estilo entre plantonistas. Toda nota sai nos mesmos
cinco campos — `ALERTA`, `IMPACTO`, `HIPÓTESE INICIAL`, `AÇÃO IMEDIATA`,
`ESCALAR PARA` — para que quem assume o turno leia sempre a mesma coisa no mesmo
lugar e não precise voltar ao alerta original.

## Decisão de método

O padrão pode ser ensinado ao modelo de duas formas: **few-shot** (mostrar notas
prontas e deixar o modelo inferir a regra) ou **especificação de schema** (dizer
o contrato campo a campo). Aqui as duas foram combinadas, com peso deliberado na
especificação:

- O **schema** carrega a regra: cinco campos, uma frase cada, gatilho de
  escalonamento verificável, proibição de inventar dado.
- Os **exemplos** carregam só tom e granularidade, e vêm marcados como tal —
  `Eles NÃO correspondem ao alerta que você vai processar agora`.

O motivo da hierarquia: few-shot puro faz o modelo copiar conteúdo dos exemplos
quando o alerta novo se parece com algum deles. Os três exemplos do padrão são
de Relay, Forge e Cerebro; os alertas reais também. Sem a marcação explícita, um
alerta de Relay tende a herdar "deploy às 09:14" do exemplo de Relay. O schema é
o que garante a regra; os exemplos apenas calibram o nível de detalhe.

## Casos de uso

- Abertura de nota assim que um alerta dispara, antes de qualquer investigação.
- Normalizar notas escritas em estilos diferentes durante um incidente longo.
- Alimentar o resumo de passagem de turno com notas já uniformes.
- Base para postmortem: a `HIPÓTESE INICIAL` registrada no momento do alerta é
  o que depois se compara com a causa-raiz confirmada.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `alerta_bruto` | ver abaixo |
| `mapa_escalonamento` | vazio (usa o default) |
| `contexto_plataforma` | `Relay: ingestão/barramento de eventos. Forge: pipeline de dados e data warehouse. Sentinel: observabilidade e alerting. Cerebro: indexação e busca.` |

**Entrada**

```
2026-05-12 14:02:09 UTC [Sentinel] autoscaler hit max replicas (60/60) on sentinel-api,
queue depth on Relay growing 2k/min, CPU avg 88%, tenant stark-industries
sending 4x baseline volume after onboarding new region
```

**Saída (Claude Sonnet 5)**

```
ALERTA: Sentinel - autoscaler no limite máximo de réplicas (60/60) em sentinel-api
IMPACTO: processamento de alerting sob pressão, fila de eventos do Relay crescendo ~2k/min
HIPÓTESE INICIAL: onboarding de nova região do tenant stark-industries elevou o volume a 4x a baseline, saturando a capacidade atual do Sentinel
AÇÃO IMEDIATA: elevar limite máximo de réplicas do autoscaler do sentinel-api e aplicar rate-limit temporário no tenant stark-industries
ESCALAR PARA: @sentinel-core se CPU permanecer acima de 85% ou a fila do Relay não estabilizar em 10min
```

Executado também contra um alerta de rejeição de ingestão no Relay e contra um
alerta de lag de consumer no Forge. Nos três, a `HIPÓTESE INICIAL` cita um fato
literal do alerta e nenhuma saída importou conteúdo dos exemplos de estilo.

## Limitações conhecidas

- A `AÇÃO IMEDIATA` é plausível, não verificada: o modelo não sabe quais ações
  o time tem de fato automatizadas. Trate como sugestão a validar, não como
  comando a executar.
- O gatilho numérico de `ESCALAR PARA` é inferido do alerta quando não há
  política de SLA na entrada. Se o time tiver limites formais, passe-os em
  `contexto_plataforma`.
- Alertas fora dos sistemas mapeados caem no fallback `@oncall-plataforma` com
  sinalização — o que evita silêncio, mas não substitui manter o mapa atualizado.
- Um alerta cru muito pobre (só código de erro, sem métrica) produz nota pobre.
  O prompt não compensa ausência de dado; ele não inventa.
