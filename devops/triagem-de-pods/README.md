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

# Triagem de saúde de pods

## Objetivo

Dar ao plantonista uma leitura confiável da saúde de um namespace em menos de
dois minutos: quais pods estão problemáticos, **por que** estão (a causa
provável, não a repetição do `STATUS`) e qual é a próxima ação.

O prompt não acessa o cluster. Ele recebe um snapshot já coletado por quem tem
acesso e trabalha só com o que está colado na entrada — sem agente, sem tool.

## Casos de uso

- Primeiro passo de plantão quando um alerta aponta para um namespace mas não
  diz o que está acontecendo dentro dele.
- Handoff de turno: o plantonista que sai cola o snapshot e entrega a triagem
  pronta para quem entra.
- Segunda opinião antes de escalar — o campo `Evidência` deixa o raciocínio
  auditável para quem receber a escalada.
- Confirmar que **não** há problema. O bloco `CASO SEM PROBLEMA` existe para
  isso e é tão importante quanto o diagnóstico: um prompt que inventa achado em
  cluster saudável queima a confiança no playbook inteiro.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `namespace` | `sentinel-prod` |
| `cluster` | `aegis-prod-use1` |
| `janela_coleta` | `2026-05-13 11:05 BRT` |
| `contexto_operacional` | `nenhum` |
| `politica_acao` | `leitura livre; ações mutantes em produção exigem aprovação do plantão` |
| `snapshot` | saída de `kubectl get pods`, `kubectl describe pod` e `kubectl logs --previous` do namespace |

**Trecho do snapshot**

```
$ kubectl get pods -n sentinel-prod
NAME                            READY   STATUS             RESTARTS       AGE
sentinel-api-7d9c8b6f4-2xk9p    1/1     Running            0              6d
sentinel-api-7d9c8b6f4-h4m2t    0/1     CrashLoopBackOff   14 (90s ago)   42m
$ kubectl describe pod sentinel-api-7d9c8b6f4-h4m2t -n sentinel-prod
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
    Limits:         memory: 512Mi
$ kubectl logs sentinel-api-7d9c8b6f4-h4m2t -n sentinel-prod --previous
2026-05-13 10:14:48 [INFO]  [cache] loading 6h alert cache (heap 410Mi/512Mi)
2026-05-13 10:15:12 [FATAL] [runtime] out of memory, shutting down process
```

**Saída (Claude Opus 5, temperatura padrão)**

```
TRIAGEM — sentinel-prod @ 2026-05-13 11:05 BRT
Veredito: DEGRADADO — sentinel-api rodando com metade da capacidade por estouro
de memória no startup.
Pods: 4 total · 3 OK · 1 problema

### 1. sentinel-api-7d9c8b6f4-h4m2t — CrashLoopBackOff · severidade ALTA
- Sintoma: 14 reinícios em 42 minutos, último há 90s; container nunca fica Ready.
- Causa provável (confiança: alta): o processo estoura o limite de 512Mi ao
  carregar o cache de alertas de 6h no startup e é morto antes de completar a
  inicialização — o ciclo se repete a cada tentativa.
- Evidência: `Reason: OOMKilled` / `Exit Code: 137`; `[cache] loading 6h alert
  cache (heap 410Mi/512Mi)` seguido de `[FATAL] out of memory` 24s depois;
  `Limits: memory: 512Mi`.
- Impacto: 1 de 2 réplicas fora. A réplica sobrevivente roda o mesmo ReplicaSet
  e o mesmo limite — se reiniciar, cai no mesmo laço e o serviço vai a zero.
- Ação agora: subir limite para 1Gi e request para 512Mi [requer aprovação].
- Se não resolver: morrer com 1Gi indica vazamento, não dimensionamento.

## Ações imediatas
1. Ajustar limite/request de memória (ou reduzir a janela do cache).
2. Confirmar que a réplica saudável segue Ready durante o rollout.

## Lacunas de coleta
- Sem `kubectl top pod`, o consumo em regime da réplica saudável é desconhecido.
```

Executado também contra um snapshot com `ImagePullBackOff` + `Pending`
(distinguiu `manifest unknown` de falha de credencial e atribuiu o `Pending` à
falta de CPU no cluster, não ao pod) e contra um snapshot saudável (veredito
`SAUDÁVEL`, sem recomendação inventada).

## Limitações conhecidas

- Cobre **um** namespace por execução; não correlaciona entre namespaces.
- Sem métricas (`kubectl top`), a análise de saturação é indireta — o prompt
  sinaliza isso em `Lacunas de coleta`, mas não substitui o dado.
- Acima de ~40 pods, o snapshot precisa ser filtrado antes de colar, sob risco
  de diluir a atenção do modelo nos pods que importam.
- A qualidade da triagem é limitada pela qualidade da coleta: sem `describe` e
  sem logs, o prompt cai no que ele mesmo proíbe — inferir a partir do `STATUS`.
- Snapshot de produção pode conter identificadores de tenant em nomes de pod e
  em logs. Sanitize antes de enviar a um provedor externo.
