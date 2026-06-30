---
name: academic-latex-production
description: Use this skill when producing, converting, editing, or reviewing LaTeX artifacts for the CabotageLens / PNV3510 Trabalho de Formatura project, especially the technical article and final TF report. It enforces academic engineering writing, LaTeX structure, citation discipline, methodological boundaries, and visual/table production rules.
---

# Academic LaTeX Production Skill — CabotageLens / PNV3510

## Purpose

This skill guides the production of LaTeX artifacts for the CabotageLens / PNV3510 Trabalho de Formatura project.

Use it as a production editor, not as a free-form content generator. The main goal is to transform validated Markdown drafts and tracked project artifacts into well-structured, compilable, academically defensible LaTeX documents.

The skill supports two main outputs:

1. **Technical article**
   - Concise, publication-oriented, paper-like structure.
   - Focused on CabotageLens as an auditable, route-aware computational framework.
   - Gustavo/Costa should appear only as compact external benchmark/plausibility evidence.

2. **Final TF report**
   - Complete academic report.
   - More detailed methodology, implementation, validation, results, discussion, limitations, appendices, and submission package.
   - Gustavo/Costa may receive fuller treatment as academic defense and benchmark evidence.

## Core project framing

The central contribution is **CabotageLens**: an auditable, route-aware computational framework/prototype for comparing direct road transport and road-cabotage-road multimodal alternatives in Brazilian freight corridors.

Frame the work as:

- an academic and engineering comparison framework;
- an auditable implementation of explicit methodological boundaries;
- a route-aware comparison of complete door-to-door alternatives;
- a conservative decision-support and research prototype;
- not a commercial freight, booking, dispatch, service-availability, or market-pricing system.

## Non-negotiable methodology boundaries

Always preserve these boundaries:

- Compare **complete door-to-door alternatives**, not ship-only versus truck-only legs.
- Baseline environmental output is **operational TTW CO₂e** unless a later tracked source explicitly changes the boundary.
- Do not mix TTW, WTW, and LCA claims.
- Do not treat CO₂, CO₂e, and CO₂eq as interchangeable unless the implemented factor and source boundary support it.
- Monetary output is a **modeled operational cost proxy**, not:
  - commercial freight;
  - market quotation;
  - tariff;
  - contract price;
  - full logistics cost;
  - economic feasibility result;
  - complete competitiveness result.
- Cabotage must not be described as universally superior to road transport.
- Gustavo/Costa is supporting benchmark/plausibility evidence, not:
  - ground truth;
  - a calibration target;
  - a complete reproduction target;
  - proof that CabotageLens is correct in magnitude.
- Port operations and hotelling must preserve provenance:
  - observed data when available;
  - weighted port-average fallback when documented;
  - documented literature/model default when justified;
  - explicit unavailable status when no defensible value exists.
- Missing port-operation or hotelling data must not be silently interpreted as zero emissions.
- Do not invent coefficients, emissions factors, fuel prices, vessel parameters, port-operation values, route data, benchmarks, or methodology claims.

## When to use this skill

Use this skill for tasks such as:

- creating a LaTeX template for the technical article;
- creating a LaTeX template for the final TF report;
- converting `docs/tf_technical_article_draft.md` to LaTeX;
- converting `docs/tf_final_report_draft.md` to LaTeX;
- splitting a large `.tex` file into chapters/sections;
- creating or reviewing LaTeX tables;
- creating figure placeholders;
- adding labels and cross-references;
- organizing appendices;
- reviewing LaTeX for methodological overclaims;
- checking citation placeholders;
- preparing a final submission checklist;
- improving academic Portuguese in LaTeX while preserving technical meaning.

Do not use this skill for:

- inventing new methodology;
- inventing missing data;
- doing new numerical analysis without explicit source data;
- replacing the validated Markdown draft as the source of truth;
- creating commercial claims about freight or market viability;
- converting citation keys into final bibliography entries without verified metadata.

## Source hierarchy

Prefer sources in this order:

1. Current user instruction.
2. Tracked repository files.
3. Validated draft files, especially:
   - `docs/tf_final_report_draft.md`
   - `docs/tf_technical_article_draft.md`
   - `docs/tf_literature_citation_map.md`
   - `docs/tf_support/**`
4. Existing app/backend code and tests, when implementation behavior matters.
5. Uploaded or cited academic sources, only when their content is available and relevant.

Never use memory or assumptions to create numerical values, bibliographic details, or methodology claims.

## Output tracks

### Track A — Technical article

Use this track when the target is a compact article.

Recommended structure:

```tex
\title{...}
\author{...}
\date{...}

\begin{abstract}
...
\end{abstract}

\section{Introdução}
\section{Contexto e revisão da literatura}
\section{Metodologia}
\section{Implementação computacional}
\section{Validação e estratégia de evidência}
\section{Resultados}
\section{Discussão}
\section{Conclusões}
```

Article writing rules:

- Keep the article concise.
- Make CabotageLens the center.
- Do not let Gustavo/Costa dominate the narrative.
- Do not compress the whole TF report mechanically.
- Prefer a clean IMRaD-like flow adapted to engineering:
  - problem;
  - literature gap;
  - method;
  - implementation;
  - validation;
  - results;
  - interpretation;
  - conclusion.
- Use compact tables only when they improve readability.
- Move excessive detail to appendices or the final report, not the article.

### Track B — Final TF report

Use this track when the target is the full report.

Recommended structure:

```tex
\chapter{Introdução}
\chapter{Objetivos}
\chapter{Revisão bibliográfica}
\chapter{Metodologia}
\chapter{Implementação computacional}
\chapter{Validação, benchmark e classificação de evidência}
\chapter{Resultados}
\chapter{Discussão}
\chapter{Limitações}
\chapter{Conclusões e trabalhos futuros}
```

Report writing rules:

- The report may be more detailed than the article.
- Preserve chapter roles:
  - Chapter 1 = problem, motivation, contribution.
  - Chapter 2 = objectives.
  - Chapter 3 = literature foundation.
  - Chapter 4 = methodology and source/boundary definitions.
  - Chapter 5 = computational implementation, operationalization, traceability.
  - Chapter 6 = validation, benchmark, evidence classification.
  - Chapter 7 = results.
  - Chapter 8 = interpretation and discussion.
  - Chapter 9 = limitations and conditions of use.
  - Chapter 10 = conclusions and future work.
- Avoid turning the report into a stitched collection of drafts.
- Reduce repeated caveats by consolidating them in the most appropriate chapter.
- Keep future work prioritized, not an unlimited wishlist.
- Appendices are appropriate for large tables, evidence inventories, validation details, and checklists.

## LaTeX production rules

### General

- Produce compilable LaTeX.
- Prefer simple, maintainable LaTeX over clever macros.
- Do not use obscure packages unless necessary.
- Use consistent labels:
  - `\label{sec:...}` for sections.
  - `\label{fig:...}` for figures.
  - `\label{tab:...}` for tables.
  - `\label{eq:...}` for equations.
- Every figure and table must have:
  - a caption;
  - a label;
  - a textual reference in the body.
- Do not leave orphan tables or figures.

### Encoding and language

For Portuguese documents, prefer:

```tex
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[brazil]{babel}
```

For modern LuaLaTeX/XeLaTeX workflows, `fontspec` may be used only if the project explicitly adopts that compiler.

### Units and notation

Use consistent notation:

- Prefer `CO$_2$e` or `\(\mathrm{CO_2e}\)` consistently in text.
- For final polished documents, prefer a project-wide macro, for example:

```tex
\newcommand{\cooe}{CO$_2$e}
\newcommand{\ttw}{\textit{tank-to-wake}}
\newcommand{\wtw}{\textit{well-to-wake}}
```

Only introduce macros if they improve consistency and do not make the file harder to maintain.

Recommended wording in Portuguese:

- `emissões operacionais TTW de CO₂e`
- `custo operacional modelado`
- `proxy operacional de custo`
- `frete comercial`
- `fronteira metodológica`
- `comparação porta a porta`
- `cadeia rodoviária-cabotagem-rodoviária`
- `evidência direcional`
- `benchmark externo`
- `reconciliação diagnóstica`
- `análise de sensibilidade`
- `proveniência dos dados`

Avoid inconsistent variants such as:

- `CO2e`, `CO₂e`, `CO2eq`, and `kgCO2e/km` mixed randomly.
- `frete` when the intended concept is modeled operational cost.
- `validação` when the intended concept is plausibility evidence or directional benchmark.

### Citations and bibliography

- Preserve existing citation keys in LaTeX form when possible:
  - Markdown `[icct2022]` can become `\cite{icct2022}` only if the bibliography workflow already supports it.
  - If no `.bib` exists or citation metadata is incomplete, keep placeholders clearly marked.
- Do not invent author names, titles, years, journals, DOIs, publishers, URLs, or access dates.
- Do not create fake BibTeX entries.
- If bibliography metadata is missing, leave an explicit TODO or unresolved citation list.
- Keep ABNT formatting for the final formatting phase, not for early conversion, unless the user explicitly asks for ABNT-ready output.

### Tables

Use tables sparingly and purposefully.

Prefer tables for:

- source/provenance inventories;
- methodological boundaries;
- scenario definitions;
- evidence classifications;
- result summaries;
- limitation matrices;
- final checklists.

Avoid huge dense tables in the main text. Move large tables to appendices.

For wide tables, consider:

```tex
\begin{table}[htbp]
\centering
\small
\caption{...}
\label{tab:...}
\begin{tabular}{p{0.24\textwidth}p{0.34\textwidth}p{0.34\textwidth}}
\hline
...
\hline
\end{tabular}
\end{table}
```

Do not use tables as a substitute for analytical discussion.

### Figures and visual elements

Prefer figure placeholders until the user explicitly provides or requests final figures.

Useful figure types for this project:

- methodology flow diagram;
- route comparison schematic;
- CabotageLens pipeline diagram;
- data provenance diagram;
- evidence-classification diagram;
- result summary plot;
- limitations/boundary diagram.

For placeholders, use:

```tex
\begin{figure}[htbp]
\centering
\fbox{\parbox{0.85\textwidth}{\centering Placeholder: description of intended figure.}}
\caption{...}
\label{fig:...}
\end{figure}
```

Do not invent visual results, maps, or charts.

### Equations

Use equations only when they clarify the method.

Every equation should define variables and units. Preserve dimensional consistency.

Example:

```tex
\begin{equation}
E = C_f \cdot FE_f
\label{eq:emissions-fuel}
\end{equation}
```

Then define:

- \(E\): emissions in kg CO₂e;
- \(C_f\): fuel consumption in kg or L, according to the implemented factor;
- \(FE_f\): emission factor in kg CO₂e per kg or L of fuel.

Do not introduce equations that are not supported by the implemented methodology.

## Academic writing rules

### Tone

Use formal Brazilian Portuguese for the TF report unless the user requests English.

Prefer:

- clear and direct phrasing;
- moderate sentence length;
- conservative academic claims;
- explicit limitations;
- strong transitions between sections.

Avoid:

- promotional language;
- exaggerated claims;
- vague statements such as "more sustainable" without boundary;
- treating assumptions as facts;
- repeating the same caveat in every section.

### Claim discipline

Replace overclaims as follows:

| Avoid | Prefer |
|---|---|
| `comprova que a cabotagem é superior` | `indica vantagem sob a fronteira e o cenário analisados` |
| `valida o modelo` | `fornece evidência de plausibilidade/direcionalidade` |
| `reproduz Gustavo/Costa` | `apresenta consistência direcional com o benchmark externo` |
| `frete estimado` | `custo operacional modelado` |
| `viabilidade comercial` | `resultado econômico parcial dentro da fronteira modelada` |
| `emissões totais` | `emissões operacionais TTW de CO₂e` |
| `resultado robusto` | `resultado compatível com a evidência disponível e suas limitações` |

### Chapter transitions

When converting or revising a report, make chapter transitions explicit:

- Chapter 1 should motivate the need for the framework.
- Chapter 2 should state what the work promises to deliver.
- Chapter 3 should show why the literature requires cautious, route-aware, boundary-explicit comparison.
- Chapter 4 should formalize the method.
- Chapter 5 should show how the software operationalizes the method.
- Chapter 6 should explain how evidence is controlled.
- Chapter 7 should report results without overinterpreting them.
- Chapter 8 should interpret what results mean.
- Chapter 9 should define limitations and conditions of use.
- Chapter 10 should close around CabotageLens as the central contribution.

## Recommended workflow

### For creating the initial LaTeX structure

1. Identify the target:
   - technical article;
   - final TF report;
   - chapter-only conversion;
   - template-only setup.
2. Inspect the relevant Markdown draft.
3. Preserve the current narrative and methodological boundaries.
4. Create minimal LaTeX structure.
5. Add labels, placeholders, and citation commands/placeholders.
6. Do not solve final bibliography formatting unless requested.
7. Run LaTeX compilation checks if a toolchain is available.
8. Report what compiles, what does not, and what remains unresolved.

### For converting Markdown to LaTeX

1. Convert headings to `\section`, `\subsection`, or `\chapter`.
2. Convert emphasis, lists, and tables carefully.
3. Convert citation placeholders only if the bibliography workflow supports them.
4. Preserve equations and units.
5. Add labels to sections, figures, tables, and equations.
6. Avoid changing substantive claims unless needed to preserve methodology boundaries.
7. Flag unresolved citations and figure/table placeholders.
8. Run a compile check if possible.

### For final polish

Check:

- Portuguese spelling and accents.
- Citation consistency.
- Figure/table numbering and references.
- Unit consistency.
- TTW/WTW/LCA wording.
- CO₂e notation.
- Cost-boundary language.
- Repeated caveats.
- Overclaim terms.
- Appendix references.
- Submission checklist.

## Validation checklist

Before returning a LaTeX artifact, verify:

- The file is syntactically reasonable LaTeX.
- The target track is clear: article or final report.
- CabotageLens remains the central contribution.
- The text does not claim universal modal superiority.
- The text does not call modeled cost "freight".
- The text does not imply commercial viability.
- The text does not mix TTW, WTW, and LCA.
- The text does not treat Gustavo/Costa as ground truth.
- All new tables and figures have captions and labels.
- All labels are unique.
- No invented citation metadata was added.
- No invented coefficients or numerical assumptions were added.
- Any unresolved references, figures, or bibliography items are clearly marked.

## Suggested final response format

When producing or revising LaTeX, respond with:

1. A concise summary of what was created or changed.
2. The file path(s) changed or created.
3. Whether compilation was checked.
4. Any unresolved citations, figures, metadata, or human-only decisions.
5. A download link or repository path when applicable.

Keep the response practical and focused.
