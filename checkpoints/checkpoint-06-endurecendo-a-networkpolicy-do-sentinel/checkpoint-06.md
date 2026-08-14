# Checkpoint 06 — Endurecendo a NetworkPolicy do Sentinel

A entrega tem duas partes: um prompt parametrizável reutilizável para endurecer
NetworkPolicies, e a condução de um ciclo de verificação e refino com as
iterações registradas.

A técnica-chave aqui é o **self-critique / verification loop** — a IA critica a
própria saída e refina. Duas decisões de método que valem explicitar: o prompt
carrega o padrão de segurança e o mapa de serviços como parâmetros, e não
embutidos no corpo; e o loop de verificação é dirigido por mim, não é a IA
decidindo sozinha quando parou.

---

## 1. O prompt parametrizável (criado via meta-prompting)

O meta-prompt que usei para gerá-lo (não faz parte da entrega, mas registro a
direção que dei à IA): *"Gere um prompt de sistema para endurecer NetworkPolicies
do Kubernetes. Ele deve receber por parâmetro o manifesto permissivo, o padrão de
segurança da org e o mapa de identidade dos serviços. Deve produzir um
default-deny explícito, regras comentadas, e nunca inventar labels. Estruture com
papel, contrato de entrada, regras invioláveis, formato de saída e um checklist
de autoverificação."* Depois refinei manualmente o contrato de saída e as
invariantes — e as regras 4 e 5 abaixo nasceram do que o próprio ciclo de
verificação encontrou.

```
# PROMPT: Endurecedor de NetworkPolicy (default-deny)

## Papel
Você é um engenheiro de segurança de plataforma revisando manifestos de
NetworkPolicy do Kubernetes. Sua função é converter uma política permissiva
em uma política default-deny mínima, liberando APENAS os fluxos legítimos
descritos no padrão fornecido.

## Parâmetros de entrada (preenchidos a cada uso)
<manifesto_permissivo>
{{MANIFESTO}}
</manifesto_permissivo>

<padrao_de_seguranca>
{{PADRAO}}          # regras de negócio: quem pode entrar, para onde sair, portas
</padrao_de_seguranca>

<mapa_de_servicos>
{{MAPA}}            # namespace + labels + portas de cada serviço citado
</mapa_de_servicos>

## Regras invioláveis
1. NUNCA use `- {}` em ingress ou egress, nem `podSelector` vazio quando o
   padrão pede seletor específico.
2. NUNCA invente labels, namespaces ou portas. Use SOMENTE os do
   <mapa_de_servicos>. Se um fluxo do padrão não tiver identidade no mapa,
   NÃO adivinhe — liste como PENDÊNCIA na saída.
3. Todo peer de ingress/egress deve combinar `namespaceSelector` +
   `podSelector` (não confie só no namespace: pods de um namespace não devem
   ser liberados em bloco a menos que o padrão diga isso).
4. Os dois seletores de um peer ficam no MESMO item da lista. Um hífen antes
   do `podSelector` cria um segundo peer e transforma o "E" em "OU", liberando
   muito mais do que se pretendia.
5. `podSelector` sozinho num peer seleciona pods do PRÓPRIO namespace da
   política, não de qualquer namespace. Sem `namespaceSelector`, o fluxo para
   outro namespace simplesmente não é liberado e a conectividade quebra sem
   erro de aplicação.
6. Egress só é completo se DNS estiver liberado — política default-deny
   quebra resolução de nome silenciosamente se DNS não for explícito. Libere
   UDP/53 e TCP/53.
7. Emita uma regra default-deny explícita e separada para o namespace.
8. Toda regra ingress/egress recebe um comentário dizendo QUAL fluxo
   legítimo ela libera.

## Formato de saída
1. Bloco YAML da(s) política(s) corrigida(s), com comentários por regra.
2. Seção "PENDÊNCIAS" (fluxos sem identidade no mapa), se houver.
3. Seção "AUTOVERIFICAÇÃO": responda a cada pergunta abaixo com
   PASSA / FALHA + justificativa de uma linha:
   - Existe default-deny explícito para ingress e egress?
   - Toda origem de ingress está no padrão? Alguma sobrou de fora?
   - Todo destino de egress está no padrão? Nenhum a mais?
   - DNS está liberado no egress, em UDP e TCP na porta 53?
   - Cada peer usa namespaceSelector + podSelector do mapa, no mesmo item
     de lista?
   - Alguma porta ou label foi inventada?
   - Sobrou algum `- {}` ou seletor vazio indevido?
```

O parâmetro `{{PROVEDOR}}` mencionado no enunciado geral não se aplica aqui: não
há troca de LLM neste artefato. Os parâmetros relevantes são manifesto, padrão e
mapa.

---

## 2. Execução: iterações v1 → verificação → v2 → verificação → v3

**Modelo:** Claude Opus 5, temperatura 0.2. Preenchi o prompt com os três
parâmetros do enunciado e conduzi o refino.

### v1 (primeira saída)

Política única, já bem melhor que o allow-all, mas com defeitos reais:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-hardened
  namespace: sentinel-prod
spec:
  podSelector:
    matchLabels:
      app: sentinel
  policyTypes: [Ingress, Egress]
  ingress:
    - from:                                    # entrada do Relay
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: relay-prod}}
    - from:                                    # entrada do API gateway
        - namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: edge}}
  egress:
    - to:                                      # saída para Forge
        - podSelector: {matchLabels: {app: forge}}
      ports: [{protocol: TCP, port: 5432}]
    - to:                                      # saída para Cerebro
        - podSelector: {matchLabels: {app: cerebro}}
      ports: [{protocol: TCP, port: 9200}]
```

### Verificação (as perguntas que um revisor de segurança faria)

Rodei o checklist de autoverificação e o cruzei com a ótica da Natasha. O que
apareceu:

1. **DNS ausente no egress.** Falha grave: com egress default-deny e sem a porta
   53, o Sentinel para de resolver `forge-prod`, `cerebro-prod` etc. A política
   se auto-sabota em produção. O checklist pegou (FALHA na pergunta de DNS).

2. **Ingress só com `namespaceSelector`.** Libera *qualquer* pod de `relay-prod`
   e de `edge`, não só o Relay e o gateway. Viola a regra 3. Um pod comprometido
   em `relay-prod` falaria com o Sentinel.

3. **Egress só com `podSelector`, sem `namespaceSelector`.** Este é o mais
   traiçoeiro dos quatro, e vale ler com atenção porque a intuição erra a
   direção do problema. Um `podSelector` sozinho dentro de um peer **não** casa
   pods em qualquer namespace: ele seleciona pods do **próprio namespace da
   política** — aqui, `sentinel-prod`. Ou seja, o efeito da v1 não é excesso de
   permissão, é o contrário: o egress para Forge e Cerebro **não é liberado
   coisa nenhuma**, e a conectividade quebra sem erro de aplicação. O manifesto
   aplica limpo, o `kubectl` não reclama, e o Sentinel para de falar com o
   warehouse. Precisa de `namespaceSelector` para alcançar outro namespace.

4. **Falta o default-deny explícito e separado.** O padrão pede política
   default-deny explícita no namespace; a v1 depende do efeito implícito de
   listar `policyTypes`. Funciona, mas não é o que o padrão exige nem o que um
   auditor quer ver.

### v2 (endereçando cada ponto)

Dividi em duas políticas — uma default-deny explícita, uma de allow — e corrigi
todos os seletores, amarrando cada peer a `namespaceSelector` + `podSelector` no
mesmo item de lista, e liberando DNS em UDP e TCP.

### Segunda verificação (v2)

O checklist passou em quase tudo. Dois pontos finos que só uma segunda passada
com olhar de SRE (Sam) e de segurança (Natasha) levanta:

5. **DNS só com UDP seria insuficiente.** Respostas grandes e algumas
   stub-resolvers usam TCP/53. Na v2 já incluí ambos, então isto passou;
   registro porque foi decisão consciente, não default.

6. **Precedência das duas políticas.** Vale confirmar a semântica em vez de
   assumir: NetworkPolicies são aditivas. Uma vez que *qualquer* política
   seleciona um pod para um `policyType`, só passa o que for explicitamente
   permitido, e as regras de allow somam-se. O `default-deny-all` não "vence" o
   `sentinel-allow`. Correto — mas é a pergunta certa a fazer.

### v3 (versão final)

Mudança pequena e de curadoria, não de correção: o `default-deny-all` com
`podSelector: {}` também captura os pods do Sentinel, e como políticas são
aditivas, o allow reabre os fluxos certos. Está correto — o ajuste foi
**documentar essa intenção no próprio manifesto**, para o próximo engenheiro não
"consertar" o que não está quebrado, e alinhar o nome da política de allow com a
convenção `<app>-allow` do padrão da Aegis.

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

Nos quatro peers acima, `namespaceSelector` e `podSelector` estão no **mesmo item
de lista** — sem hífen antes do `podSelector`. É isso que faz a condição ser
"namespace X **E** label Y". Com o hífen, viraria "namespace X **OU** label Y", e
a política liberaria o namespace de origem inteiro. É um caractere de diferença
entre a política que a Natasha aprova e a que ela barra de novo.

A v3 é o que entra na biblioteca como saída de referência.

---

## 3. Curadoria (o que eu, e não a IA, decidi)

**Separar em duas políticas** (default-deny explícito + allow), em vez da
política única da v1. O padrão da Aegis pede default-deny *explícito*; a versão
de política única atende ao efeito, mas não ao requisito auditável. Decisão de
padrão, não de correção técnica.

**Amarrar todo peer a namespace + pod.** A v1 estava "certa o suficiente" para
parecer funcionar e "errada o bastante" para ser insegura no ingress — o tipo de
brecha que passa em teste e falha em auditoria. Elevei isso a regra inviolável do
prompt (regra 3) para que qualquer uso futuro herde a exigência.

**A regra 5 é o achado que mais me custou.** Minha primeira leitura do defeito de
egress da v1 foi a intuitiva e estava errada: assumi que `podSelector` sozinho
casaria pods de qualquer namespace, o que faria da v1 uma política permissiva
demais. É o contrário — o seletor fica preso ao namespace da política, e o efeito
real é quebra silenciosa de conectividade. As duas leituras levam à mesma
correção (`namespaceSelector` obrigatório), e é justamente por isso que o erro
sobreviveria à revisão: a conclusão certa esconde a premissa errada. Virou regra
explícita no prompt porque um revisor que entende o mecanismo errado descreve o
risco errado no post-mortem — e o próximo a ler o playbook aprende errado.

**DNS como regra inviolável do prompt**, não como achado pontual. Esquecer DNS em
egress default-deny é o erro mais comum e o mais silencioso; codifiquei na regra
6 para que o playbook nunca mais o cometa.

**Parar em v3.** O loop poderia seguir, mas as rodadas seguintes só produziriam
microajustes cosméticos. A decisão de encerrar é minha — o critério foi "todas as
perguntas do revisor de segurança respondidas com PASSA e nenhuma identidade
inventada". Um loop de self-critique sem critério de parada definido por fora
roda para sempre, porque sempre existe uma crítica a mais a fazer.

**Limite honesto.** Validei a **semântica** e a **conformidade com o padrão**, mas
o teste real é `kubectl apply --dry-run=server` mais um teste de conectividade em
cluster — o Sam quer isso no pipeline. O prompt entrega um artefato correto por
construção; a validação em cluster é o gate que fecha o checkpoint, e é
exatamente o tipo de teste automatizado que os checkpoints finais vão cobrar da
biblioteca. O passo natural é transformar o checklist de autoverificação em
asserts executáveis — um teste que rejeita qualquer política sem regra de DNS ou
com `- {}` é trivial de escrever e é o que torna o item "testado em pipeline" de
verdade.
