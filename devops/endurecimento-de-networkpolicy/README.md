---
nome: Endurecimento de NetworkPolicy
descricao: Converte um manifesto de NetworkPolicy permissivo em política default-deny mínima, com regras comentadas e autoverificação de segurança.
versao: 1.0.0
tags: [kubernetes, seguranca, networkpolicy, hardening, revisao]
inputs:
  - nome: manifesto
    descricao: Manifesto de NetworkPolicy permissivo a ser endurecido, como submetido à revisão.
  - nome: padrao
    descricao: Regras do padrão de segurança da organização — quem pode entrar, para onde sair, quais portas, exigências de default-deny e comentários.
  - nome: mapa_servicos
    descricao: Identidade de cada serviço citado no padrão — namespace, labels de pod e portas. É a única fonte de seletores permitida.
---

# Endurecimento de NetworkPolicy

## Objetivo

Transformar um `allow-all` disfarçado de política em uma default-deny mínima,
onde cada regra libera um fluxo nomeado e comentado. O prompt não confia no bom
senso do modelo: as oito regras invioláveis codificam os erros que essa tarefa
produz por default, incluindo os dois que passam em teste de conectividade e
falham em auditoria.

O `mapa_servicos` é a peça que impede o pior comportamento — inventar labels.
Sem ele o modelo escreve `app: forge` porque soa plausível; com ele, um fluxo
sem identidade mapeada vira `PENDÊNCIA` em vez de chute.

A seção de `AUTOVERIFICAÇÃO` é parte do artefato, não enfeite: é ela que
sustenta o ciclo de crítica e refino documentado abaixo.

## Casos de uso

- Endurecer uma política permissiva barrada em revisão de segurança.
- Escrever a primeira NetworkPolicy de um namespace que hoje roda sem nenhuma.
- Revisar política existente: passe-a em `manifesto` e veja o que a
  autoverificação reprova.
- Padronizar políticas entre namespaces mantendo `padrao` fixo e trocando só o
  `mapa_servicos`.

## Exemplo de uso — com o ciclo de verificação e refino

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `manifesto` | política `sentinel-allow` com `podSelector: {}`, `ingress: [{}]` e `egress: [{}]` |
| `padrao` | ingress só de Relay e do API gateway; egress só para Forge (5432), Cerebro (9200) e DNS interno; sem allow-all; default-deny explícito; toda regra comentada |
| `mapa_servicos` | Sentinel → ns `sentinel-prod`, `app=sentinel`; Relay → ns `relay-prod`, `app=relay`; API gateway → ns `edge`, `app=api-gateway`; Forge → ns `forge-prod`, `app=forge`, 5432; Cerebro → ns `cerebro-prod`, `app=cerebro`, 9200; DNS → ns `kube-system`, `k8s-app=kube-dns`, 53 |

### v1 — primeira saída

Política única, muito melhor que o allow-all, mas com defeitos reais: ingress
apenas com `namespaceSelector`, egress apenas com `podSelector`, sem DNS e sem
default-deny separado.

### Verificação — o que um revisor de segurança levanta

1. **DNS ausente no egress.** Com egress default-deny e sem a porta 53, o
   Sentinel para de resolver `forge-prod` e `cerebro-prod`. A política se
   auto-sabota em produção. A autoverificação pegou (FALHA na pergunta de DNS).
2. **Ingress só com `namespaceSelector`.** Libera *qualquer* pod de
   `relay-prod` e de `edge`, não só o Relay e o gateway. Um pod comprometido em
   `relay-prod` falaria com o Sentinel.
3. **Egress só com `podSelector`.** Um `podSelector` sozinho num peer seleciona
   pods do **próprio namespace da política** — ou seja, `sentinel-prod`. O
   efeito não é excesso de permissão: é que o egress para Forge e Cerebro
   **simplesmente não é liberado**, e a conectividade quebra sem erro de
   aplicação. Precisa de `namespaceSelector` para alcançar o outro namespace.
4. **Falta o default-deny explícito e separado.** O padrão exige política
   default-deny explícita; a v1 dependia do efeito implícito de listar
   `policyTypes`. Funciona, mas não é o que o padrão pede nem o que um auditor
   quer ver.

### v2 — endereçando cada ponto

Dividida em duas políticas (default-deny explícita + allow mínimo), todos os
peers amarrados a `namespaceSelector` + `podSelector` no mesmo item de lista, e
DNS liberado em UDP e TCP.

### Segunda verificação (v2)

5. **DNS só com UDP seria insuficiente.** Respostas grandes e algumas
   stub-resolvers usam TCP/53. A v2 já incluiu ambos — registrado porque foi
   decisão consciente, não default.
6. **Precedência das duas políticas.** NetworkPolicies são aditivas: uma vez
   que qualquer política seleciona um pod para um `policyType`, só passa o que
   for explicitamente permitido, e as regras de allow somam-se. O default-deny
   não "vence" o allow. Correto — mas era a pergunta certa a fazer, não algo a
   assumir.

### v3 — versão final

Ajuste de curadoria, não de correção: documentar no próprio manifesto a
intenção da coexistência das duas políticas (para o próximo engenheiro não
"consertar" o que não está quebrado) e alinhar o nome à convenção `<app>-allow`.

```yaml
# (1) default-deny explícito para todo o namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sentinel-prod
spec:
  podSelector: {}                 # todos os pods do namespace
  policyTypes: [Ingress, Egress]  # sem regras ingress/egress = nega tudo
---
# (2) allow mínimo para os pods do Sentinel
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow
  namespace: sentinel-prod
  annotations:
    # Coexiste com default-deny-all. NetworkPolicies são aditivas:
    # o deny nega tudo por padrão, este allow reabre só os fluxos legítimos.
    # Não remover default-deny-all supondo redundância.
    security.aegis/reviewed-by: "natasha-romanoff"
spec:
  podSelector:
    matchLabels: {app: sentinel}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:                       # entrada: Relay consumindo eventos
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: relay-prod}}
          podSelector: {matchLabels: {app: relay}}
    - from:                       # entrada: API gateway da plataforma
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: edge}}
          podSelector: {matchLabels: {app: api-gateway}}
  egress:
    - to:                         # saída: Forge / warehouse Postgres
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: forge-prod}}
          podSelector: {matchLabels: {app: forge}}
      ports: [{protocol: TCP, port: 5432}]
    - to:                         # saída: Cerebro / busca Elasticsearch
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: cerebro-prod}}
          podSelector: {matchLabels: {app: cerebro}}
      ports: [{protocol: TCP, port: 9200}]
    - to:                         # saída: DNS interno (resolução de nomes)
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: kube-system}}
          podSelector: {matchLabels: {k8s-app: kube-dns}}
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
```

Nos quatro peers acima, `namespaceSelector` e `podSelector` estão no **mesmo
item de lista** — sem hífen antes do `podSelector`. É o que faz a condição ser
"namespace X **E** label Y". Com o hífen, viraria "namespace X **OU** label Y",
liberando todo o namespace de origem.

### Por que parou na v3

Critério de encerramento: todas as perguntas do revisor de segurança
respondidas com PASSA e nenhuma identidade inventada. As rodadas seguintes só
produziriam microajuste cosmético. A decisão de parar é humana — não é a IA que
decide quando o refino acabou.

## Limitações conhecidas

- Valida **semântica** e **conformidade com o padrão**, não conectividade real.
  O gate que fecha de verdade é `kubectl apply --dry-run=server` mais um teste
  de conectividade em cluster.
- Assume que o namespace de origem tem a label `kubernetes.io/metadata.name`.
  Ela é populada automaticamente pelo Kubernetes desde a 1.21; em clusters mais
  antigos, o seletor precisa de outra label e o `mapa_servicos` deve dizer qual.
- Não cobre `ipBlock` para destinos externos ao cluster. Egress para internet
  ou para serviço gerenciado fora do cluster fica de fora e aparece como
  PENDÊNCIA.
- A política resultante depende do CNI ter suporte a NetworkPolicy. Em cluster
  sem suporte, o manifesto aplica e não faz nada — falha totalmente silenciosa.
- A autoverificação é o modelo checando a si mesmo. Ela pega os erros
  catalogados nas regras, não os que ninguém previu. Não substitui revisão
  humana.
