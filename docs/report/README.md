# Relatório final em LaTeX

Este diretório contém a primeira estrutura LaTeX modular do relatório final de TF do CabotageLens.

## Estrutura

- `main.tex`: preâmbulo, capa, resumo, listas, capítulos, apêndices e bibliografia.
- `chapters/`: capítulos 1 a 10 do relatório.
- `appendices/`: apêndices de parâmetros/proveniência, validação e checklist de reprodutibilidade.

## Compilação esperada

A partir de `docs/report/`:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Se usar outro fluxo, mantenha os caminhos relativos: a bibliografia aponta para `../references.bib`.

## Onde editar

Edite o texto acadêmico nos arquivos de `chapters/`. Edite material denso, listas de parâmetros e checks de submissão em `appendices/`. Evite colocar conteúdo novo diretamente em `main.tex`, exceto metadados institucionais, macros ou ajustes de estilo.

## Bibliografia

Esta primeira versão usa `\bibliographystyle{plain}` e `../references.bib`. A formatação ABNT/USP e a revisão completa de metadados bibliográficos permanecem como TODO de produção final.

## TODOs conhecidos

- Escrever o abstract final em inglês.
- Trocar placeholders de figuras por diagramas finais.
- Revisar captions, labels e paginação após compilação real.
- Definir estilo bibliográfico final.

## Status atual

Estrutura criada a partir de `docs/tf_final_report_draft.md` e dos artefatos rastreados do projeto. A compilação depende de uma instalação LaTeX disponível no ambiente local.
