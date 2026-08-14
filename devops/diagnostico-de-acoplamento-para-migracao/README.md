---
nome: Diagnóstico de acoplamento para migração
descricao: Mapeia acoplamentos, invariantes e falhas silenciosas de um sistema antes de qualquer proposta de migração. Elo 1 da cadeia de migração.
versao: 1.0.0
tags: [migracao, arquitetura, pipeline-de-dados, cadeia-de-prompts, diagnostico]
inputs:
  - nome: nome_sistema
    descricao: Nome do sistema a migrar (ex.: Forge).
  - nome: snapshot_estado_atual
    descricao: Estado atual do sistema — ingestão, transformação, destino e pontos frágeis conhecidos.
  - nome: dependentes
    descricao: Consumidores do sistema e o que cada um espera dele (formato, cadência, garantias).
  - nome: objetivo_migracao
    descricao: Estado-alvo desejado após a migração.
  - nome: restricoes
    descricao: Restrições inegociáveis da migração (sem big-bang, reversibilidade, SLAs a preservar).
---

# Diagnóstico de acoplamento para migração

> **Elo 1 de 3** da cadeia de migração de arquitetura.
> Próximo elo: [plano-faseado-de-migracao](../plano-faseado-de-migracao/).

## Objetivo

Fotografar o sistema **antes** de propor qualquer mudança. Produz o insumo que
os dois elos seguintes consomem: o mapa de acoplamentos, as invariantes
numeradas e os modos de falha silenciosa de cada dependente.

A instrução mais importante do prompt é a proibição: `NÃO proponha ainda o plano
de migração`. Sem ela o modelo pula direto para a solução e o diagnóstico sai
raso — e um diagnóstico raso envenena a cadeia inteira, porque os elos 2 e 3
constroem em cima dele. Este é o elo de maior alavancagem e o único que vale ler
linha a linha antes de deixar seguir.

A numeração das invariantes (`I1`, `I2`, ...) não é cosmética: é o que permite
ao elo 2 dizer "esta fase protege I3" e ao elo 3 amarrar um portão de validação
a uma invariante específica.

## Casos de uso

- Antes de planejar qualquer migração de arquitetura com consumidores a
  jusante — batch para streaming, monólito para serviços, troca de storage.
- Levantar o que **não pode quebrar** quando o conhecimento está espalhado pela
  cabeça de várias pessoas.
- Auditar uma migração já em andamento: rode o diagnóstico e compare as
  invariantes encontradas com as que o plano em execução protege.
- Isoladamente, sem o resto da cadeia, como mapa de dependências de um sistema
  legado que ninguém documentou.

## Exemplo de uso

**Parâmetros**

| Parâmetro | Valor |
|---|---|
| `nome_sistema` | `Forge` |
| `snapshot_estado_atual` | job em cron a cada 60min (`forge-batch-ingest`); 14 etapas encadeadas em Spark, ~40min; grava em tabelas do warehouse particionadas por hora; se um lote falha, o próximo acumula o dobro |
| `dependentes` | Sentinel (lê tabelas agregadas), Cerebro (indexa eventos transformados), relatórios de billing (rodam de madrugada) |
| `objetivo_migracao` | consumir do Relay continuamente, processando em pequenos blocos no lugar do lote de 1h |
| `restricoes` | manter dependentes funcionando durante a transição; nada de virada única; cada passo reversível |

**Configuração de execução:** Claude Opus 4.8, temperatura `0.2` (biblioteca
exige reprodutibilidade).

**Forma da saída esperada** — quatro seções nomeadas, das quais o resto da
cadeia depende:

```markdown
## Acoplamentos
| Dependente | O que consome | Formato | Cadência |
| Sentinel   | tabelas agregadas por hora | ... | ... |

## Invariantes
- **I1** — a partição horária do warehouse permanece completa e imutável ...
- **I2** — o billing lê um fechamento estável de madrugada ...

## Riscos priorizados
| Risco | Impacto | Probabilidade | Por quê |
| Dupla contagem em janela de agregação | Alto | Média | ... |

## Falhas silenciosas por dependente
- **Billing** — soma parcial sem erro: a query retorna, o número é menor.
```

> Nota de estado: a saída integral desta execução (e a dos elos 2 e 3) não foi
> arquivada nesta versão. Ao rodar a cadeia, salve o output dos três elos como
> golden e trate qualquer diff futuro como mudança a revisar.

**Testes estruturais** (baratos, verificam contrato e não conteúdo):

- [ ] Saída contém as 4 seções com os nomes exatos.
- [ ] `## Riscos priorizados` é tabela com colunas impacto e probabilidade.
- [ ] Invariantes numeradas `I1`, `I2`, ...
- [ ] Nenhuma proposta de plano de migração presente.
- [ ] Cada dependente de `dependentes` aparece em falhas silenciosas.

## Limitações conhecidas

- O diagnóstico só enxerga o que está em `snapshot_estado_atual` e
  `dependentes`. Consumidor não declarado — o script de alguém, o dashboard
  esquecido — não aparece, e é exatamente o que quebra em migração.
- As invariantes saem em linguagem natural, não como asserts executáveis. A
  tradução para teste é trabalho humano.
- O modelo às vezes tenta contrabandear recomendação dentro do campo "por quê"
  dos riscos. Vale checar na revisão linha a linha.
- Sistemas muito grandes estouram o contexto quando a saída inteira é colada no
  elo 2. Nesses casos, insira um passo de compactação que preserve invariantes
  e riscos priorizados.
