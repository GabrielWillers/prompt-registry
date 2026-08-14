# Checkpoint 07 — A biblioteca vira código

## Entrega

**Repositório:** https://github.com/GabrielWillers/prompt-registry

Fork de [`fabricioveronez/prompt-registry`](https://github.com/fabricioveronez/prompt-registry),
com o histórico do template preservado como base. Os prompts dos Checkpoints 01
a 06 foram migrados para as convenções dele: categoria como pasta na raiz, um
prompt por subpasta, `prompt.md` + `README.md` com frontmatter idêntico.

Os seis checkpoints viraram **oito prompts**, todos em `devops/` — a cadeia de
migração do CP05 são três prompts distintos, porque a regra "um prompt por pasta"
vale mesmo quando eles se encadeiam.

| Origem | Pasta no repositório |
|---|---|
| CP01 — triagem de pods | `devops/triagem-de-pods/` |
| CP02 — nota de triagem | `devops/nota-de-triagem/` |
| CP03 — causa-raiz | `devops/causa-raiz/` |
| CP04 — backpressure do Relay | `devops/decisao-de-arquitetura-com-tradeoffs/` |
| CP05 — migração do Forge (elo 1) | `devops/diagnostico-de-acoplamento-para-migracao/` |
| CP05 — migração do Forge (elo 2) | `devops/plano-faseado-de-migracao/` |
| CP05 — migração do Forge (elo 3) | `devops/runbook-de-fase-de-migracao/` |
| CP06 — NetworkPolicy do Sentinel | `devops/networkpolicy-sentinel/` |

Cada prompt nasceu em `versao: 1.0.0`. Commits semânticos com escopo na
categoria (`feat(devops): adiciona prompt de triagem de pods`), e os três índices
— raiz, categoria e `CLAUDE.md` — atualizados na mesma entrega.

---

## Um prompt no formato completo

`devops/triagem-de-pods/` — o item mais completo dos oito.

### `prompt.md`

```markdown
---
nome: Triagem de saúde de pods
descricao: Transforma um snapshot estático de um namespace Kubernetes em triagem com causa provável por pod e próxima ação do plantão.
versao: 1.0.0
tags: [kubernetes, sre, plantao, triagem, incidentes]
inputs:
  - nome: snapshot
    descricao: Saída colada de kubectl get pods, kubectl describe e kubectl logs do namespace, coletada por quem tem acesso ao cluster.
  - nome: namespace
    descricao: Namespace Kubernetes ao qual o snapshot se refere.
  - nome: cluster
    descricao: Identificador do cluster. Use "não informado" quando não houver.
  - nome: janela_coleta
    descricao: Data e hora em que o snapshot foi coletado. Use "não informada" quando não houver.
  - nome: contexto_operacional
    descricao: Deploys recentes, incidentes abertos ou mudanças de infra. Use "nenhum" quando não houver.
  - nome: politica_acao
    descricao: O que o plantonista pode executar por conta própria e o que exige aprovação.
---

## PAPEL
Você é um SRE sênior de plantão, especialista em Kubernetes e em diagnóstico sob
pressão. Seu leitor é um plantonista que pode ter sido acordado agora e precisa
decidir a próxima ação em menos de dois minutos.

## TAREFA
Fazer a triagem de um SNAPSHOT ESTÁTICO de um namespace Kubernetes: identificar
os pods em estado problemático, determinar a causa provável de cada um e
recomendar a próxima ação do plantão.

Você NÃO tem acesso ao cluster. Tudo o que você sabe está no SNAPSHOT abaixo.

## PARÂMETROS
- NAMESPACE: {{namespace}}
- CLUSTER: {{cluster}}
- JANELA_COLETA: {{janela_coleta}}
- CONTEXTO_OPERACIONAL: {{contexto_operacional}}
- POLITICA_ACAO: {{politica_acao}}

[... método em 6 passos, critérios de classificação, regras de evidência,
     formato de saída e o bloco CASO SEM PROBLEMA ...]

## SNAPSHOT
{{snapshot}}
```

Os seis `{{placeholders}}` do corpo são exatamente os seis itens de `inputs`. É
o ponto do checkpoint: **os parâmetros do prompt e o campo `inputs` são a mesma
coisa**, agora declarada e versionada em vez de combinada de boca.

### `README.md`

Começa com o **mesmo frontmatter**, byte a byte, e abaixo traz a camada humana:

```markdown
---
nome: Triagem de saúde de pods
descricao: Transforma um snapshot estático de um namespace Kubernetes em triagem...
versao: 1.0.0
tags: [kubernetes, sre, plantao, triagem, incidentes]
inputs:
  - nome: snapshot
    descricao: Saída colada de kubectl get pods, kubectl describe e kubectl logs...
  [...]
---

# Triagem de saúde de pods

## Objetivo
Dar ao plantonista uma leitura confiável da saúde de um namespace em menos de
dois minutos: quais pods estão problemáticos, **por que** estão (a causa
provável, não a repetição do `STATUS`) e qual é a próxima ação.

## Casos de uso
- Primeiro passo de plantão quando um alerta aponta para um namespace...
- Handoff de turno...
- Confirmar que **não** há problema. O bloco `CASO SEM PROBLEMA` existe para
  isso e é tão importante quanto o diagnóstico...

## Exemplo de uso
[tabela de parâmetros preenchidos + trecho do snapshot + saída real do modelo]

## Limitações conhecidas
- Cobre **um** namespace por execução; não correlaciona entre namespaces.
- Sem métricas (`kubectl top`), a análise de saturação é indireta...
- Acima de ~40 pods, o snapshot precisa ser filtrado antes de colar...
- Snapshot de produção pode conter identificadores de tenant. Sanitize antes de
  enviar a um provedor externo.
```

---

## Nota de mapeamento

O encaixe foi de **normalização, não de reescrita** — o playbook já nascia com
contrato de parâmetros declarado, então o trabalho foi traduzir esse contrato
para a forma do template. Sete decisões, registradas no `CLAUDE.md` do fork para
valerem daqui em diante:

1. **`inputs` é o contrato, não decoração.** O que estava em
   `parametros_obrigatorios` / `parametros_opcionais` virou `inputs`, e cada item
   ganhou `descricao`. É onde os parâmetros passam a ser documentados de fato.

2. **Placeholders normalizados para `snake_case`.** Vieram em `{{MAIÚSCULAS}}`;
   a convenção do template é `{{nome_variavel}}`.

3. **Sem sintaxe de default no placeholder.** `{{CLUSTER|não informado}}` não
   existe no template — `inputs` não tem campo de default. O fallback foi para a
   `descricao` do input e para o corpo do prompt.

4. **Provedor e modelo saíram do corpo do prompt.** A cadeia do CP05 injetava
   `[MODELO] {{PROVEDOR_MODELO}}`; dizer ao modelo qual modelo ele é não muda a
   saída. Modelo, temperatura e exigência de roteamento (o endpoint sem retenção
   do CP03) viraram metadados de execução no `README.md`. É a decisão em que mais
   me afasto do enunciado geral, que lista "o provedor" entre os parâmetros.

5. **Pasta nomeada pelo resultado, não pela técnica.** O CP04 virou
   `decisao-de-arquitetura-com-tradeoffs`, não `tree-of-thought`.

6. **Cadeia vira um prompt por pasta.** Os três elos do CP05 são pastas
   independentes. O acoplamento é declarado no `README.md` de cada elo (elo
   anterior / próximo elo) e o contrato de handoff — nomes de seção padronizados,
   invariantes numeradas — fica escrito no próprio `prompt.md`.

7. **O frontmatter do CP03 encolheu.** Ele tinha campos próprios (`roteamento`,
   `pre_processamento`) fora do padrão. O conteúdo não se perdeu: a exigência de
   sanitização upstream virou a seção **"Pré-requisito de compliance"** no
   `README.md`, com destaque maior do que tinha antes.

---

## Validação

Antes de publicar, rodei uma checagem automática das convenções nos 8 prompts:

- frontmatter **idêntico** entre `prompt.md` e `README.md` (a "duplicação
  consciente" que o template exige);
- campos obrigatórios presentes: `nome`, `descricao`, `versao`, `tags`, `inputs`;
- `versao: 1.0.0` em todos;
- 2 a 5 tags por prompt;
- **`inputs` batendo exatamente com os `{{placeholders}}`** do corpo — nem
  parâmetro documentado que não existe no prompt, nem placeholder sem
  documentação.

Os 8 passam.

Um defeito escapou dessa checagem e só apareceu quando o GitHub renderizou a
página: `descricao: Sistema sob análise (ex.: Cerebro, Forge...)` é **YAML
inválido** — dois-pontos seguido de espaço encerra a chave dentro de um escalar
sem aspas. O GitHub mostrou *"mapping values are not allowed in this context"* e
o frontmatter não renderizou. Estava em 8 arquivos (4 prompts × 2 arquivos, por
causa da duplicação consciente). Corrigido no commit
`fix(devops): escapa dois-pontos no frontmatter que quebrava o parser YAML`, e a
validação passou a rodar um parser YAML de verdade em vez de conferir só os
campos.

É o argumento prático a favor de tratar a biblioteca como código: a convenção só
vale se algo a verifica. Essa checagem é candidata natural ao pipeline dos
checkpoints 09/10.
