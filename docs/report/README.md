# Relatório final em LaTeX

Este diretório contém a primeira estrutura LaTeX modular do relatório final de TF do CabotageLens.

## Estrutura

- `main.tex`: preâmbulo, capa, resumo, listas, capítulos, apêndices e bibliografia.
- `chapters/`: capítulos 1 a 10 do relatório.
- `appendices/`: apêndices de parâmetros/proveniência, validação e checklist de reprodutibilidade.

## Compilação esperada

A partir de `docs/report/`:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

O relatório usa `biblatex` com backend `biber`; se a compilação for manual, execute a sequência equivalente com `pdflatex`, `biber`, `pdflatex` e `pdflatex`. Se usar outro fluxo, mantenha os caminhos relativos: a bibliografia aponta para `../references.bib`.

## Onde editar

Edite o texto acadêmico nos arquivos de `chapters/`. Edite material denso, listas de parâmetros e checks de submissão em `appendices/`. Evite colocar conteúdo novo diretamente em `main.tex`, exceto metadados institucionais, macros ou ajustes de estilo.

## Bibliografia

Esta versão usa `biblatex` com `../references.bib` e suprime, na renderização, campos internos de nota/arquivo usados apenas como rastreabilidade do repositório. A formatação ABNT/USP e a revisão completa de metadados bibliográficos permanecem como pendências de produção final.

## Pendências conhecidas

- Trocar placeholders de figuras por diagramas finais.
- Revisar captions, labels e paginação após compilação real.
- Definir estilo bibliográfico final.

## Status atual

Estrutura criada a partir de `docs/tf_final_report_draft.md` e dos artefatos rastreados do projeto. A compilação depende de uma instalação LaTeX disponível no ambiente local.
