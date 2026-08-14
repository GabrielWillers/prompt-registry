# DevOps

Prompts voltados a **infraestrutura, automação e operação** de sistemas: pipelines de CI/CD, containers, orquestração, provisionamento, observabilidade, confiabilidade e segurança operacional.

## Escopo

Entram aqui prompts relacionados a:

- Pipelines de CI/CD (GitHub Actions, GitLab CI, Jenkins etc.).
- Containers e orquestração (Docker, Kubernetes, Helm).
- Infraestrutura como código (Terraform, Pulumi, Ansible).
- Provedores de nuvem (AWS, GCP, Azure) e seus recursos.
- Observabilidade (logs, métricas, tracing, alertas, dashboards).
- Confiabilidade, SRE, postmortems e análise de incidentes.
- Segurança operacional (hardening, secrets, políticas de acesso).

## Fora de escopo

- Escrita de código de aplicação → usar `desenvolvimento/`.
- Conteúdo educacional sobre DevOps (aulas, artigos, vídeos) → usar `criacao-conteudo/`.

## Prompts

Os prompts abaixo formam o **playbook de IA operacional da Aegis**: a biblioteca
que o time de engenharia usa para operar a plataforma de observabilidade
(Relay, Forge, Sentinel e Cerebro). Todos recebem os dados variáveis por
parâmetro — nenhum serve a um caso só.

### Operação e plantão

- [triagem-de-pods](./triagem-de-pods/) — transforma um snapshot estático de um namespace Kubernetes em triagem com causa provável por pod e próxima ação do plantão.
- [nota-de-triagem-de-alerta](./nota-de-triagem-de-alerta/) — converte um alerta bruto de monitoramento na nota de triagem padronizada de cinco campos usada na passagem de turno.
- [causa-raiz-de-degradacao](./causa-raiz-de-degradacao/) — cruza configuração, métricas e logs de uma janela de incidente para chegar à causa-raiz com cadeia causal ancorada em evidência.

### Decisão de arquitetura

- [decisao-de-arquitetura-com-tradeoffs](./decisao-de-arquitetura-com-tradeoffs/) — compara caminhos alternativos contra restrições duras e brandas antes de recomendar, expondo o que cada opção sacrifica.

### Migração de arquitetura (cadeia de 3 elos)

Os três prompts abaixo formam uma **cadeia**: a saída de cada elo é a entrada do
seguinte. Podem ser usados isoladamente, mas foram desenhados para rodar em
sequência.

1. [diagnostico-de-acoplamento-para-migracao](./diagnostico-de-acoplamento-para-migracao/) — mapeia acoplamentos, invariantes e falhas silenciosas de um sistema antes de qualquer proposta de migração.
2. [plano-faseado-de-migracao](./plano-faseado-de-migracao/) — quebra uma migração em fases incrementais e reversíveis a partir do diagnóstico, com critério de saída e rollback por fase.
3. [runbook-de-fase-de-migracao](./runbook-de-fase-de-migracao/) — detalha uma fase do plano como runbook executável, com portões de validação e rollback com critério objetivo de abort.

### Segurança operacional

- [endurecimento-de-networkpolicy](./endurecimento-de-networkpolicy/) — converte um manifesto de NetworkPolicy permissivo em política default-deny mínima, com regras comentadas e autoverificação de segurança.
