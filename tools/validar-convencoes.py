#!/usr/bin/env python3
"""Valida as convenções do catálogo sem chamar modelo nenhum.

Roda em segundos e custa zero. É a primeira camada do gate: pega o tipo de
defeito que já quebrou este repositório na prática — frontmatter YAML inválido
que o GitHub não renderiza, e divergência entre `inputs` e os `{{placeholders}}`
do corpo do prompt.

Saída: lista de problemas em stdout; código 1 se houver algum.
"""
from __future__ import annotations

import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML não instalado: pip install pyyaml")

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
OBRIGATORIOS = ("nome", "descricao", "versao", "tags", "inputs")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SECOES_README = ("## Objetivo", "## Casos de uso", "## Exemplo de uso", "## Limitações conhecidas")


def frontmatter(caminho: str):
    texto = open(caminho, encoding="utf-8").read()
    m = FRONTMATTER.match(texto)
    if not m:
        return None, texto, "sem bloco de frontmatter"
    try:
        return yaml.safe_load(m.group(1)), texto[m.end():], None
    except yaml.YAMLError as e:
        # Foi exatamente este caso que quebrou a renderização no GitHub:
        # `descricao: Sistema sob análise (ex.: Cerebro)` — dois-pontos seguido
        # de espaço encerra a chave dentro de um escalar sem aspas.
        return None, texto, f"YAML inválido — {str(e).splitlines()[0]}"


def main() -> int:
    problemas: list[str] = []
    prompts = sorted(glob.glob("*/*/prompt.md"))
    if not prompts:
        problemas.append("nenhum prompt.md encontrado — rode da raiz do repositório")

    for caminho_prompt in prompts:
        pasta = os.path.dirname(caminho_prompt)
        caminho_readme = os.path.join(pasta, "README.md")

        fm_p, corpo, erro = frontmatter(caminho_prompt)
        if erro:
            problemas.append(f"{caminho_prompt}: {erro}")
            continue
        if not os.path.exists(caminho_readme):
            problemas.append(f"{pasta}: README.md ausente")
            continue
        fm_r, corpo_readme, erro_r = frontmatter(caminho_readme)
        if erro_r:
            problemas.append(f"{caminho_readme}: {erro_r}")
            continue

        # A "duplicação consciente" do template só funciona se for verificada.
        if fm_p != fm_r:
            problemas.append(f"{pasta}: frontmatter difere entre prompt.md e README.md")

        for campo in OBRIGATORIOS:
            if campo not in (fm_p or {}):
                problemas.append(f"{caminho_prompt}: campo obrigatório ausente — {campo}")

        versao = str((fm_p or {}).get("versao", ""))
        if not SEMVER.match(versao):
            problemas.append(f"{caminho_prompt}: versao '{versao}' não é semver")

        tags = (fm_p or {}).get("tags") or []
        if not 2 <= len(tags) <= 5:
            problemas.append(f"{caminho_prompt}: {len(tags)} tag(s); a convenção pede de 2 a 5")

        # inputs é o CONTRATO de parâmetros: tem de bater com o corpo, nos dois sentidos.
        declarados = {i["nome"] for i in ((fm_p or {}).get("inputs") or []) if isinstance(i, dict) and "nome" in i}
        usados = set(re.findall(r"\{\{(\w+)\}\}", corpo))
        if declarados - usados:
            problemas.append(f"{pasta}: input declarado e não usado no prompt — {', '.join(sorted(declarados - usados))}")
        if usados - declarados:
            problemas.append(f"{pasta}: placeholder sem input documentado — {', '.join(sorted(usados - declarados))}")

        for secao in SECOES_README:
            if secao not in corpo_readme:
                problemas.append(f"{caminho_readme}: seção obrigatória ausente — {secao}")

        # Se existe suíte, ela precisa ser YAML válido e apontar para o prompt certo.
        caminho_cfg = os.path.join(pasta, "promptfooconfig.yaml")
        if os.path.exists(caminho_cfg):
            try:
                cfg = yaml.safe_load(open(caminho_cfg, encoding="utf-8"))
            except yaml.YAMLError as e:
                problemas.append(f"{caminho_cfg}: YAML inválido — {str(e).splitlines()[0]}")
                continue
            if "file://prompt.md" not in (cfg.get("prompts") or []):
                problemas.append(f"{caminho_cfg}: não referencia file://prompt.md")
            if not cfg.get("tests"):
                problemas.append(f"{caminho_cfg}: sem casos de teste")

    print(f"{len(prompts)} prompt(s) verificado(s).")
    if problemas:
        print(f"\n{len(problemas)} problema(s):\n")
        for p in problemas:
            print(f"  - {p}")
        return 1
    print("Todas as convenções batem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
