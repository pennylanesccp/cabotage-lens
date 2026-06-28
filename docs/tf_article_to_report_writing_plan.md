# Article-to-TF Final Report Writing Plan

## 1. Purpose

This document defines how to expand the concise technical article into the final Trabalho de Formatura (TF) report.

The article in `docs/tf_technical_article_draft.md` is the concise source narrative: it establishes the argument flow, the contribution, the conservative result interpretation, and the order in which the reader should encounter the method, evidence, discussion, limitations, and conclusions.

The final TF report is the expanded academic version of that article. It should add literature depth, methodological detail, tables, limitations, appendices, and institutional formatting, but it should not change the central claims. The TF derives from the article, not the other way around.

This plan is deliberately granular so a future coding-agent task can draft exactly one subsection, validate it against the source artifacts, and stop before moving to the next subsection.

This plan does not create the final TF text, rewrite the technical article, rerun validation, add sources, or change model outputs.

## 2. Source hierarchy

Use the following hierarchy whenever drafting, reviewing, or resolving conflicts in the final TF report.

1. `docs/validation/tf_final_result_synthesis.md`
   - Source of truth for results, thesis-use categories, allowed claims, prohibited claims, sensitivity classifications, Batch 002 interpretation, and final safe wording.
2. `docs/tf_technical_article_draft.md`
   - Source narrative and argument flow. The final TF should expand this article, not restart from an empty report outline.
3. `docs/tf_final_report_draft.md`
   - Academic scaffold and expanded report structure. Use it to align subsection placement, report tone, and body-chapter coverage.
4. `docs/tf_literature_citation_map.md`
   - Source of truth for allowed citation placeholders, safe citation use, and misuse boundaries.
5. Validation, benchmark, and boundary artifacts
   - `docs/validation/tf_validation_batch_002_gustavo_benchmark.md`
   - `docs/validation/tf_validation_batch_002_rerun_comparison.md`
   - `docs/validation/tf_validation_batch_002_road_factor_reconciliation.md`
   - `docs/validation/tf_sensitivity_results_batch_001b.md`
   - `docs/validation/tf_validation_batch_001b_methodology_decisions.md`
   - `docs/tf_system_boundary.md`
   - `docs/port_ops_model.md`

Conflict-resolution rules:

- Result conflicts: follow `docs/validation/tf_final_result_synthesis.md`.
- Narrative conflicts: follow `docs/tf_technical_article_draft.md`, unless the final synthesis says otherwise.
- Academic-structure conflicts: follow `docs/tf_final_report_draft.md`.
- Citation-use conflicts: follow `docs/tf_literature_citation_map.md`.
- Boundary conflicts: preserve the narrower or more conservative boundary.
- Do not introduce new results, citations, assumptions, routes, ports, distances, formulas, factors, model parameters, workbook values, or metadata.

## 3. Expansion principles

- Expand from the article, not from scratch.
- Preserve the article's argument order unless there is a clear academic-report reason to split one article section across multiple TF chapters.
- Write one subsection at a time.
- Every drafted subsection must name the source article section used.
- Preserve conservative claims from the final synthesis.
- Do not overclaim cabotage superiority.
- Do not promote sensitive, benchmark-mismatched, not-comparable, blocked, excluded, reference-needed, or historical-diagnostic cases to robust evidence.
- Keep TTW, WTW, LCA, CO2, and CO2e boundaries explicit.
- Keep model cost estimates separate from commercial freight rates.
- Preserve units and dimensional consistency.
- Use only citation placeholders already allowed by `docs/tf_literature_citation_map.md`.
- Treat literature as context, boundary framing, limitation support, or future-work support unless a tracked methodology artifact explicitly authorizes direct model use.
- Keep observed results separate from interpretation. Results chapters should report what was observed; Discussion should explain what it means and what it does not mean.
- Do not collapse cost and emissions into a single winner unless a decision rule is explicitly introduced in tracked methodology.
- Keep the final TF defensible for a Naval Engineering undergraduate thesis: transparent, auditable, route-aware, and conservative about evidence quality.

## 4. Final TF target structure

Pre-textual elements are final formatting and submission items. Handle them later, mainly in issue #26:

- cover page / folha de rosto;
- acknowledgements, if needed;
- resumo;
- abstract;
- list of figures;
- list of tables;
- abbreviations / symbols, if useful;
- table of contents.

The body-writing workflow should focus first on the technical chapters below.

### 1. Introduction

Target subsections:

- 1.1 Context and motivation: Brazilian freight dependence on road transport and relevance of cabotage.
- 1.2 Problem statement: why truck-vs-ship comparisons are insufficient without door-to-door boundaries.
- 1.3 Research question / guiding question: how to compare road-only and road-cabotage-road alternatives under explicit cost and emissions boundaries.
- 1.4 Contribution: CabotageLens as an auditable, route-aware computational framework.
- 1.5 Scope and boundaries: operational TTW CO2e, modeled cost, not commercial freight, not WTW/LCA.
- 1.6 Report structure.

Source article section(s):

- `Resumo`
- `1. Introducao`
- `9. Conclusoes`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/tf_final_report_draft.md`
- `docs/tf_literature_citation_map.md`
- `docs/tf_system_boundary.md`

Purpose in the final report:

- Establish why the comparison matters, why door-to-door boundaries matter, and why CabotageLens is framed as a defensible computational framework instead of a universal modal-ranking tool.

Key claims to preserve:

- Brazilian freight has strong road dependence and cabotage is relevant for some long-distance flows.
- Direct truck-vs-ship comparisons are insufficient without pre-carriage, maritime leg, on-carriage, port choice, distance provenance, and explicit boundaries.
- CabotageLens compares road-only and road-cabotage-road alternatives under operational TTW CO2e and modeled-cost boundaries.
- The contribution is methodological and computational, not a claim of universal cabotage superiority.

Claims to avoid:

- Cabotage is universally better.
- CabotageLens is a commercial freight quote engine.
- Current outputs are WTW/LCA results.
- The final report has calibrated validation before the Results and Discussion prove the claim.

Expected tables/figures/appendices:

- No major table required in the Introduction.
- Optional schematic figure of the problem boundary, only if reused consistently from methodology.
- Cross-reference to Appendix for allowed/prohibited claim checklist.

Important drafting rule:

- Finalize the Introduction late, after Methodology, Results, Discussion, Limitations, and Conclusions are stable.

### 2. Objectives and Contribution

Target subsections:

- 2.1 General objective.
- 2.2 Specific objectives.
- 2.3 Scientific/engineering contribution.
- 2.4 What the work does not claim.

Source article section(s):

- `1. Introducao`
- `3. Metodologia`
- `4. Implementacao computacional`
- `9. Conclusoes`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/tf_final_report_draft.md`
- `docs/tf_system_boundary.md`

Purpose in the final report:

- Make the work's purpose and contribution explicit before literature and methodology details.

Key claims to preserve:

- Framework/tool development is the main contribution.
- The tool compares road-only and road-cabotage-road alternatives with route and distance provenance.
- Outputs are operational TTW CO2e and modeled cost estimates.
- Evidence is classified conservatively and interpreted with benchmark awareness.

Claims to avoid:

- Full logistics optimization.
- Full supernetwork modeling.
- Commercial freight-rate prediction.
- Exact reproduction of the Gustavo/Costa workbook.
- Robust headline-candidate results.

Expected tables/figures/appendices:

- Optional compact objective table mapping objective to method/result chapter.
- Appendix can carry an allowed/prohibited claim checklist.

### 3. Literature Review and Positioning

Target subsections:

- 3.1 Brazilian cabotage and BR do Mar context.
- 3.2 Short sea shipping and modal-shift evidence.
- 3.3 Door-to-door comparison and multimodal logistics.
- 3.4 Supernetwork/commercial-freight studies and why CabotageLens is not a full supernetwork.
- 3.5 Emissions boundaries: TTW, WTW, LCA, CO2, and CO2e.
- 3.6 Port operations, hoteling, and port-boundary relevance.
- 3.7 Literature gap addressed by CabotageLens.

Source article section(s):

- `2. Posicionamento na literatura`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/tf_literature_citation_map.md`
- `docs/tf_final_report_draft.md`
- `docs/tf_system_boundary.md`
- `docs/port_ops_model.md`

Purpose in the final report:

- Position CabotageLens against existing literature without turning the chapter into a generic literature dump.

Key claims to preserve:

- Literature supports the need for route-aware, door-to-door, corridor-specific comparisons.
- Short sea/cabotage advantages are conditional.
- Supernetwork and commercial-freight studies cover broader operational dimensions than CabotageLens.
- WTW, LCA, CO2-only, and commercial-rate references must be kept separate from current TTW CO2e and modeled-cost outputs.
- Port operations and hoteling matter, but the current model has a defined operational boundary.

Claims to avoid:

- Literature values validate route-level CabotageLens outputs.
- WTW/LCA literature calibrates the current TTW baseline.
- Brazilian supernetwork literature means CabotageLens already models service frequency, schedule, inventory, or commercial freight rates.
- Port hotelling papers validate a full modal-shift comparison.

Expected tables/figures/appendices:

- Literature-positioning table: source key, safe use, boundary, and limitation.
- Optional appendix copy of citation-use controls if the main text would become too dense.

Important drafting rule:

- Every literature subsection must explain why the source matters for this method and its limitations.

### 4. System Boundary and Methodology

Target subsections:

- 4.1 Functional unit and cargo basis.
- 4.2 Road-only alternative.
- 4.3 Road-cabotage-road alternative.
- 4.4 Port selection and route construction.
- 4.5 Road distance provenance and routing provider/cache logic.
- 4.6 Maritime distance provenance and fallback hierarchy.
- 4.7 Road fuel, cost, and emissions model.
- 4.8 Maritime fuel, cost, and emissions model.
- 4.9 Port operations and hoteling treatment.
- 4.10 Modeled-cost boundary.
- 4.11 Operational TTW CO2e boundary.
- 4.12 Result-quality and thesis-use classification.

Source article section(s):

- `3. Metodologia`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/tf_system_boundary.md`
- `docs/port_ops_model.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/validation/tf_validation_batch_001b_methodology_decisions.md`
- `docs/validation/tf_sensitivity_results_batch_001b.md`
- `docs/validation/tf_validation_batch_002_road_factor_reconciliation.md`

Purpose in the final report:

- Define exactly what is compared, how route legs are represented, what boundaries govern interpretation, and how result quality is classified.

Key claims to preserve:

- The functional unit is a specified mass of containerized cargo between an origin and destination in Brazil; validation artifacts repeatedly use 1 TEU / 14 t per shipment.
- The compared alternatives are road-only and road-cabotage-road.
- Road distance, maritime distance, port choices, and result classifications must preserve provenance.
- Cost outputs are model cost estimates.
- Emissions outputs are operational TTW CO2e.
- Haversine fallback is screening evidence only.
- The road-factor reconciliation is diagnostic, not a replacement baseline.

Claims to avoid:

- New formulas or factors not already tracked.
- Treating a fallback maritime distance as validation.
- Treating Pecem as Porto de Fortaleza or Suape as Porto do Recife.
- Treating the diagnostic road factor as a model update.
- Treating cost estimates as commercial freight rates.

Expected tables/figures/appendices:

- Functional-unit and boundary table.
- Route-chain diagram or table: road-only vs road-cabotage-road legs.
- Distance-provenance table.
- Result-classification table.
- Appendix for detailed classification inventory if the main text would become too large.

Important drafting rule:

- Keep this chapter technical, explicit, and formula-aware, but do not invent formulas or factors not already tracked.

### 5. Computational Implementation of CabotageLens

Target subsections:

- 5.1 System overview.
- 5.2 User inputs and scenario parameters.
- 5.3 Route construction pipeline.
- 5.4 Data/cache layer and Supabase role.
- 5.5 Output artifacts: distances, costs, emissions, warnings, provenance.
- 5.6 Reproducibility and audit trail.

Source article section(s):

- `4. Implementacao computacional`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/tf_final_report_draft.md`
- `docs/tf_system_boundary.md`
- `docs/port_ops_model.md`
- `docs/validation/tf_validation_batch_002_rerun_comparison.md`
- `docs/validation/tf_validation_run_manifest.md`

Purpose in the final report:

- Explain enough of the implementation to support reproducibility and academic defensibility without writing a code manual.

Key claims to preserve:

- Streamlit UI orchestrates the application, with reusable domain logic in modules and tracked CLI workflows for reproducibility.
- Supabase Postgres supports route/provider caches and auditability.
- Outputs include distances, costs, emissions, selected ports, warnings, and provenance.
- Cache behavior matters for traceability; Batch 002 rerun showed 63 route-cache hits and 0 misses.

Claims to avoid:

- CabotageLens solves a complete logistics network.
- The implementation guarantees real service availability or commercial prices.
- Cache/provider stability means all magnitude gaps are resolved.

Expected tables/figures/appendices:

- Implementation component table: app, modules, scripts, data, migrations.
- Pipeline figure or sequence table.
- Appendix for code/module inventory if useful.

Important drafting rule:

- This is not a code manual. Include only enough implementation detail to support reproducibility and academic defensibility.

### 6. Validation, Benchmark, and Evidence-Classification Strategy

Target subsections:

- 6.1 Why validation is not treated as a single pass/fail result.
- 6.2 Historical Batch 001 as diagnostic evidence.
- 6.3 Batch 001B methodology-decision layer.
- 6.4 Issue #16 sensitivity runs.
- 6.5 Batch 002 Gustavo/Costa external benchmark.
- 6.6 Supabase/cache rerun as route-provider stability check.
- 6.7 Road-factor reconciliation as diagnostic benchmark alignment.
- 6.8 Final thesis-use categories and claim controls.

Source article section(s):

- `5. Estrategia de validacao e benchmark`

Source artifacts:

- `docs/validation/tf_final_result_synthesis.md`
- `docs/validation/tf_validation_batch_001b_methodology_decisions.md`
- `docs/validation/tf_sensitivity_results_batch_001b.md`
- `docs/validation/tf_validation_batch_002_gustavo_benchmark.md`
- `docs/validation/tf_validation_batch_002_rerun_comparison.md`
- `docs/validation/tf_validation_batch_002_road_factor_reconciliation.md`
- `docs/tf_literature_citation_map.md`

Purpose in the final report:

- Explain the evidence-control logic before presenting Results, so readers understand why some rows are sensitivity-only, not-comparable, excluded, or benchmark-limited.

Key claims to preserve:

- Validation is layered: diagnostic history, methodology decisions, internal sensitivity, external benchmark, cache rerun, diagnostic road-factor reconciliation, and final synthesis categories.
- Batch 001 is historical diagnostic evidence.
- Batch 001B improves auditability and classifies cases.
- Issue #16 executed three sensitivity rows, all `sensitive`.
- Batch 002 supports directional consistency for 21 positive supported OD pairs, not calibrated magnitude.
- Cache rerun reduces concern that road-route provider instability is the main cause of the road gap.
- Road-factor reconciliation explains much of the road-side mismatch, but does not recalibrate CabotageLens.

Claims to avoid:

- Single pass/fail validation.
- Exact reproduction of the Gustavo/Costa workbook.
- Treating the workbook as ground truth.
- Treating diagnostic reconciliation as model replacement.
- Promoting any current result to `headline_candidate`.

Expected tables/figures/appendices:

- Evidence-layer table.
- Thesis-use category table.
- Claim-control table.
- Appendix for full validation status tables.

Important drafting rule:

- This chapter should explain how evidence is classified before presenting results.

### 7. Results

Target subsections:

- 7.1 Final case inventory and thesis-use categories.
- 7.2 Internal sensitivity results.
- 7.3 Batch 002 benchmark results.
- 7.4 Supabase/cache rerun results.
- 7.5 Road-factor reconciliation results.
- 7.6 Synthesis of safe numerical interpretation.

Source article section(s):

- `6. Resultados`

Source artifacts:

- `docs/validation/tf_final_result_synthesis.md`
- `docs/validation/tf_sensitivity_results_batch_001b.md`
- `docs/validation/tf_validation_batch_002_gustavo_benchmark.md`
- `docs/validation/tf_validation_batch_002_rerun_comparison.md`
- `docs/validation/tf_validation_batch_002_road_factor_reconciliation.md`

Purpose in the final report:

- Present observed results and classifications, while keeping interpretation mostly for Discussion.

Key claims to preserve:

- No current `headline_candidate` result exists.
- Three executed sensitivity rows are Santos/Manaus reference distance, Manaus/Pecem alternate port, and Rio Grande/Suape alternate port.
- Those rows remain `sensitive`.
- Batch 002 achieved 21/21 directional alignment for supported positive OD pairs.
- Baseline magnitude mismatch is not calibrated validation.
- Road-factor reconciliation reduced mean/median road mismatch from 199.8%/149.3% to 43.9%/19.6%.

Claims to avoid:

- Treating sensitivity rows as robust baseline conclusions.
- Treating Batch 002 as exact reproduction.
- Treating road-factor reconciliation as a recalibrated baseline.
- Mixing WTW/LCA with TTW CO2e.
- Reading model costs as commercial freight rates.

Expected tables/figures/appendices:

- Final case inventory summary.
- Sensitivity results table.
- Batch 002 benchmark summary table.
- Supabase/cache rerun summary table.
- Road-factor reconciliation summary table.
- Appendix for full Batch 002 and detailed case inventory tables.

Important drafting rule:

- Separate observed numbers from interpretation. Interpretation belongs mainly in Discussion.

### 8. Discussion

Target subsections:

- 8.1 What the evidence supports.
- 8.2 What the evidence does not support.
- 8.3 Why directional consistency matters but does not prove calibrated magnitude.
- 8.4 Why the road-side benchmark gap is methodologically explainable.
- 8.5 Route, port, distance, cargo/allocation, and service-boundary implications.
- 8.6 Cost boundary versus commercial freight.
- 8.7 Emissions boundary implications: TTW versus WTW/LCA.
- 8.8 Engineering value of an auditable framework.

Source article section(s):

- `7. Discussao`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/tf_literature_citation_map.md`
- `docs/tf_system_boundary.md`
- `docs/validation/tf_validation_batch_002_rerun_comparison.md`
- `docs/validation/tf_validation_batch_002_road_factor_reconciliation.md`

Purpose in the final report:

- Convert the observed results into a conservative engineering interpretation that is useful but not overstated.

Key claims to preserve:

- Evidence supports an auditable, boundary-explicit framework and directional consistency in the named evidence layers.
- Directional agreement matters, but magnitude mismatch prevents calibrated validation.
- Road fuel and emission-factor assumptions explain much of the road-side mismatch.
- Route, port, maritime distance, cargo allocation, service availability, cost boundary, and emissions boundary all affect interpretation.
- The engineering value is transparency, traceability, and conservative classification.

Claims to avoid:

- Universal cabotage-superiority claims.
- Treating workbook mismatch as simple model failure or simple workbook truth.
- Treating favorable sensitivity results as final corridor proof.
- Combining cost and emissions into a single winner without a decision rule.

Expected tables/figures/appendices:

- Discussion can reference Results tables rather than repeat them.
- Optional table: evidence supports / evidence does not support.
- Appendix for claim-control checklist.

Important drafting rule:

- Discussion should explicitly avoid universal cabotage-superiority claims.

### 9. Limitations

Target subsections:

- 9.1 Environmental boundary limitations.
- 9.2 Cost-boundary limitations.
- 9.3 Route, port, and maritime-distance limitations.
- 9.4 Service availability, frequency, and supernetwork limitations.
- 9.5 Gustavo/Costa benchmark comparability limitations.
- 9.6 Sensitivity-only and not-comparable evidence limitations.
- 9.7 Implementation/data limitations.

Source article section(s):

- `8. Limitacoes`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/tf_system_boundary.md`
- `docs/port_ops_model.md`
- `docs/tf_literature_citation_map.md`
- `docs/validation/tf_validation_batch_002_gustavo_benchmark.md`
- `docs/validation/tf_sensitivity_results_batch_001b.md`

Purpose in the final report:

- Show that the thesis understands exactly where the evidence boundary is.

Key claims to preserve:

- Environmental results are operational TTW CO2e, not WTW or LCA.
- Costs are model estimates, not commercial freight rates.
- Maritime distance, port selection, route construction, service availability, frequency, cargo allocation, and benchmark comparability remain limiting factors.
- Sensitivity-only rows remain sensitivity evidence.
- Not-comparable and skipped rows remain outside headline conclusions.

Claims to avoid:

- Weakening the project unnecessarily.
- Framing all limitations as failures.
- Suggesting limitations invalidate the auditable-framework contribution.
- Inventing solutions or sources that are not tracked.

Expected tables/figures/appendices:

- Limitation-to-future-work table.
- Appendix for detailed blocked/excluded/reference-needed cases.

Important drafting rule:

- Limitations should be precise and boundary-aware, not apologetic.

### 10. Conclusions and Future Work

Target subsections:

- 10.1 Main conclusion.
- 10.2 Methodological contribution.
- 10.3 Evidence-based findings.
- 10.4 Practical/engineering implications.
- 10.5 Future work.

Source article section(s):

- `9. Conclusoes`
- `10. Trabalhos futuros`

Source artifacts:

- `docs/tf_technical_article_draft.md`
- `docs/validation/tf_final_result_synthesis.md`
- `docs/tf_final_report_draft.md`
- `docs/tf_literature_citation_map.md`

Purpose in the final report:

- Close the report with the strongest defensible claims: contribution, evidence-supported findings, practical implications, and targeted future work.

Key claims to preserve:

- CabotageLens provides an auditable, reproducible, boundary-explicit framework.
- Evidence supports cautious directional interpretation, not calibrated magnitude validation.
- The main contribution is methodological and computational.
- Batch 001B and Batch 002 improve traceability and benchmark-aware interpretation.

Claims to avoid:

- Universal superiority of cabotage.
- Exact workbook reproduction.
- Commercial freight-rate equivalence.
- WTW/LCA conclusions from TTW CO2e outputs.

Expected tables/figures/appendices:

- No large table required in the conclusion.
- Future work can be a concise bullet list.
- Appendices should carry detailed inventories, not the conclusion.

Future work should include:

- WTW/LCA expansion.
- Complete Gustavo/Costa cargo/allocation/route reconciliation.
- Improved selected-port and maritime-distance evidence.
- Commercial freight, time, reliability, tariffs, frequency, and inventory costs.
- Supernetwork evolution.
- Expanded validation references.

### References

References are handled mainly in issue #26. Until final formatting, use only citation placeholders approved in `docs/tf_literature_citation_map.md`.

### Appendices

Use appendices for material that would overload the main text:

- detailed case inventory;
- validation status tables;
- full Batch 002 benchmark tables;
- road-factor reconciliation table;
- allowed/prohibited claim checklist;
- reproducibility commands, if useful;
- code/module inventory, if useful.

Do not put appendix-level detail in the main narrative unless it is necessary to understand the argument.

## 5. Article-to-TF mapping table

Use this table as the subsection-level writing tracker. Each row is small enough to become a separate future coding-agent task.

Status values:

- `not_started`
- `source_article_ready`
- `needs_subsection_draft`
- `needs_human_review`
- `ready_for_final_polish`

| Article section | TF chapter | TF subsection | Source artifact(s) | Allowed citation placeholders | Key claim to preserve | Added detail needed in TF | Claims to avoid | Expected table/figure/appendix | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Resumo`; `1. Introducao` | 1. Introduction | 1.1 Context and motivation | Article; synthesis; citation map | `[icct2022]`, `[competitiveness2024]`, `[modalshiftreview2020]` | Road dependence motivates route-aware cabotage comparison. | Add Brazilian context and explain why context does not validate route-level results. | Cabotage is automatically better; national averages validate model outputs. | None; optional context figure later. | `source_article_ready` |
| `1. Introducao` | 1. Introduction | 1.2 Problem statement | Article; system boundary; citation map | `[shortsea2019]`, `[modalshiftreview2020]`, `[competitiveness2024]` | Truck-vs-ship comparisons are insufficient without door-to-door boundaries. | Explicitly name pre-carriage, maritime leg, on-carriage, port choice, and distance provenance. | Ship-only comparisons prove corridor superiority. | Optional route-chain schematic. | `source_article_ready` |
| `1. Introducao` | 1. Introduction | 1.3 Research question / guiding question | Article; final report scaffold; system boundary | None required; optional `[modalshiftreview2020]` | The question is how to compare road-only and road-cabotage-road alternatives under explicit cost and emissions boundaries. | Phrase as guiding engineering question rather than a hypothesis that promises superiority. | A yes/no universal modal winner. | None. | `source_article_ready` |
| `Resumo`; `1. Introducao`; `9. Conclusoes` | 1. Introduction | 1.4 Contribution | Article; synthesis; final report scaffold | None required; optional `[competitiveness2024]` for contrast | CabotageLens is an auditable, route-aware computational framework. | Contrast framework contribution with supernetwork and quotation-engine exclusions. | Full supernetwork; commercial freight quote engine. | None. | `source_article_ready` |
| `1. Introducao`; `3. Metodologia` | 1. Introduction | 1.5 Scope and boundaries | Article; system boundary; citation map | `[competitiveness2024]`, `[decarb2024]`, `[maritimelca2024]` only as contrast/future work | Outputs are operational TTW CO2e and model cost estimates. | State not WTW/LCA, not commercial freight, not complete logistics optimization. | TTW equals WTW/LCA; model cost equals freight rate. | Boundary summary table can be deferred to Chapter 4. | `source_article_ready` |
| `1. Introducao` | 1. Introduction | 1.6 Report structure | Article; final report scaffold | None | The report expands the article into academic chapters. | Summarize chapters after their content is stable. | Promising results not supported later. | None. | `not_started` |
| `1. Introducao`; `9. Conclusoes` | 2. Objectives and contribution | 2.1 General objective | Article; final report scaffold; system boundary | None | Develop and document CabotageLens as an auditable comparison framework. | Convert article contribution into one academic objective sentence. | Claiming full operational planning or market pricing. | Objective table optional. | `source_article_ready` |
| `3. Metodologia`; `4. Implementacao computacional`; `5. Estrategia de validacao e benchmark` | 2. Objectives and contribution | 2.2 Specific objectives | Article; final report scaffold; synthesis | None | Objectives cover route-aware comparison, explicit boundaries, provenance, outputs, and conservative classification. | Add bullet list tied to method and validation chapters. | Objectives that require untracked reruns or new data. | Objective-to-chapter table optional. | `source_article_ready` |
| `4. Implementacao computacional`; `9. Conclusoes` | 2. Objectives and contribution | 2.3 Scientific/engineering contribution | Article; synthesis; final report scaffold | `[competitiveness2024]` only for contrast | Contribution is methodological/computational, with route and distance provenance and benchmark-aware interpretation. | Explain naval-engineering relevance: auditable assumptions, route construction, boundary control. | Calibrated validation; universal modal ranking. | None. | `source_article_ready` |
| `1. Introducao`; `8. Limitacoes` | 2. Objectives and contribution | 2.4 What the work does not claim | Article; synthesis; citation map | `[shortsea2019]`, `[modalshiftreview2020]`, `[competitiveness2024]` | The work does not claim universal superiority, commercial rates, WTW/LCA, exact workbook reproduction, or robust headline cases. | Add a concise negative-claim list tied to prohibited claims. | Softening boundaries to make stronger claims. | Appendix: allowed/prohibited claim checklist. | `source_article_ready` |
| `2. Posicionamento na literatura` | 3. Literature review | 3.1 Brazilian cabotage and BR do Mar context | Article; citation map; final report scaffold | `[icct2022]`, `[competitiveness2024]` | Brazilian cabotage context motivates the problem but does not validate model outputs. | Add policy/modal context and safe-use caveats. | National values as route-level validation. | Literature safe-use table. | `source_article_ready` |
| `2. Posicionamento na literatura` | 3. Literature review | 3.2 Short sea shipping and modal-shift evidence | Article; citation map; final report scaffold | `[shortsea2019]`, `[modalshiftreview2020]` | Short sea/cabotage advantages are conditional and corridor-specific. | Expand evidence on utilization, corridor, service, and barriers. | Cabotage always emits less. | Literature safe-use table. | `source_article_ready` |
| `2. Posicionamento na literatura`; `3. Metodologia` | 3. Literature review | 3.3 Door-to-door comparison and multimodal logistics | Article; citation map; system boundary | `[shortsea2019]`, `[modalshiftreview2020]`, `[competitiveness2024]` | Door-to-door boundaries matter because road access and ports affect results. | Link literature to the road-cabotage-road structure used in methodology. | Ship leg alone is enough for comparison. | Route-chain figure can be referenced from Chapter 4. | `source_article_ready` |
| `2. Posicionamento na literatura` | 3. Literature review | 3.4 Supernetwork/commercial-freight studies | Article; citation map; final report scaffold | `[competitiveness2024]`, `[modalshiftreview2020]` | CabotageLens is not a full supernetwork or freight quotation model. | Explain service frequency, inventory, rates, and network constraints as outside current scope. | CabotageLens models full commercial competitiveness. | Literature comparison table. | `source_article_ready` |
| `2. Posicionamento na literatura`; `3. Metodologia` | 3. Literature review | 3.5 Emissions boundaries | Article; citation map; system boundary | `[decarb2024]`, `[maritimelca2024]`, `[competitiveness2024]`, `[shortsea2019]`, `[icct2022]` | Current output is operational TTW CO2e; WTW/LCA/CO2-only evidence is boundary contrast. | Define TTW, WTW, LCA, CO2, CO2e and safe citation roles. | WTW/LCA values calibrate TTW output. | Boundary table. | `source_article_ready` |
| `2. Posicionamento na literatura`; `3. Metodologia` | 3. Literature review | 3.6 Port operations, hoteling, and port-boundary relevance | Article; citation map; port ops model | `[berth2009]`, `[shipops2022]`, `[berthairquality2010]`, `[decarb2024]` | Port operations and hoteling matter, but current treatment is bounded and model-based. | Connect literature to port-ops model limits and future improvements. | Port papers validate full route-level model. | Port boundary table or appendix note. | `source_article_ready` |
| `2. Posicionamento na literatura`; `9. Conclusoes` | 3. Literature review | 3.7 Literature gap addressed by CabotageLens | Article; citation map; synthesis | `[competitiveness2024]`, `[shortsea2019]`, `[modalshiftreview2020]` | Gap is an auditable, route-aware, boundary-explicit framework for TF-scale comparison. | Synthesize why CabotageLens sits between generic modal claims and full supernetwork models. | Claiming the gap is solved for commercial operations. | None. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.1 Functional unit and cargo basis | Article; system boundary; synthesis; Batch 002 benchmark | None required | Functional unit is specified containerized cargo between Brazilian origin/destination; validation often uses 1 TEU / 14 t. | Explain per shipment, per tonne, per TEU, and benchmark comparability caveats. | Cargo/allocation equivalence with workbook is fully reconciled. | Functional-unit table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.2 Road-only alternative | Article; system boundary; final report scaffold | None required | Road-only is direct heavy-truck transport from origin to destination. | Add distance, fuel, cost, and TTW CO2e chain at conceptual level. | New fuel formulas/factors. | Route-chain table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.3 Road-cabotage-road alternative | Article; system boundary; port ops model | None required | Multimodal chain is pre-carriage, maritime leg, port operations/hoteling if modeled, and on-carriage. | Add leg definitions, units, and double-counting caution. | Treating sea leg alone as the whole multimodal alternative. | Route-chain table/diagram. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.4 Port selection and route construction | Article; methodology decisions; synthesis | `[competitiveness2024]` only for network contrast | Port selection is deterministic/auditable but not service optimization. | Explain nearest-port heuristic, forced ports, and alternate-port status. | Pecem equals Fortaleza; Suape equals Recife; selected ports imply service availability. | Port-selection caveat table. | `source_article_ready` |
| `3. Metodologia`; `4. Implementacao computacional` | 4. Methodology | 4.5 Road distance provenance and routing provider/cache logic | Article; Batch 002 rerun; final report scaffold | None required | Road distances come from routing/cache logic and carry provenance. | Explain ORS/cache role and the Batch 002 cache stability check without turning it into Results. | Cache stability proves calibrated magnitude. | Provider/cache provenance table. | `source_article_ready` |
| `3. Metodologia`; `5. Estrategia de validacao e benchmark` | 4. Methodology | 4.6 Maritime distance provenance and fallback hierarchy | Article; methodology decisions; sensitivity results; synthesis | `[shortsea2019]` only for route-specific caution | Maritime distance source type controls result confidence. | Explain SeaMatrix, haversine fallback, external reference, unit conversion `1 nm = 1.852 km`, and forced-port provenance. | Fallback validates corridor; nearby-port reference validates selected port. | Distance provenance table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.7 Road fuel, cost, and emissions model | Article; final report scaffold; road-factor reconciliation | None required | Road outputs use implemented baseline model; diagnostic road factor is separate. | Describe conceptual distance x fuel x factor chain and benchmark diagnostic separation. | Replacing baseline with `0.8602944 kgCO2e/km`. | Formula-aware concept table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.8 Maritime fuel, cost, and emissions model | Article; final report scaffold; system boundary | None required | Maritime outputs depend on distance, vessel class/intensity, fuel, cost, and TTW CO2e boundary. | Add model components only where tracked; avoid untracked vessel details. | Inventing vessel parameters or service speeds. | Formula-aware concept table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.9 Port operations and hoteling treatment | Article; port ops model; system boundary | `[berth2009]`, `[shipops2022]`, `[berthairquality2010]` as method/context only | Port operations and hoteling are included when modeled under the operational TTW CO2e boundary. | Explain moves basis, port calls, hoteling caveat, and model-cost boundary. | Full terminal tariffs; WTW/LCA substitution; double counting. | Port-ops component table. | `source_article_ready` |
| `3. Metodologia` | 4. Methodology | 4.10 Modeled-cost boundary | Article; system boundary; citation map | `[competitiveness2024]`, `[modalshiftreview2020]`, `[icct2022]` as context only | Costs are model estimates, not commercial freight rates. | List included and excluded cost categories. | Freight-rate equivalence; tariffs/margins included when not modeled. | Cost boundary table. | `source_article_ready` |
| `3. Metodologia`; `2. Posicionamento na literatura` | 4. Methodology | 4.11 Operational TTW CO2e boundary | Article; system boundary; citation map | `[decarb2024]`, `[maritimelca2024]`, `[competitiveness2024]`, `[icct2022]` as contrast/future work | Emissions are operational TTW CO2e per shipment unless stated otherwise. | Define exclusions and comparison risks. | TTW equals WTW/LCA; CO2-only equals CO2e. | Emissions boundary table. | `source_article_ready` |
| `3. Metodologia`; `5. Estrategia de validacao e benchmark` | 4. Methodology | 4.12 Result-quality and thesis-use classification | Article; synthesis; methodology decisions | None required | Final use categories control what each row can support. | Define `headline_candidate`, `sensitivity_discussion`, `benchmark_supports_direction`, `not_comparable`, etc. | Treating classifications as cosmetic labels. | Classification table; appendix full inventory. | `source_article_ready` |
| `4. Implementacao computacional` | 5. Implementation | 5.1 System overview | Article; final report scaffold | None | CabotageLens is a Streamlit app with reusable modules and CLI workflows. | Summarize app/modules/scripts/data/migrations roles. | Code manual; deployment guide. | Component table. | `source_article_ready` |
| `4. Implementacao computacional` | 5. Implementation | 5.2 User inputs and scenario parameters | Article; port ops model; system boundary | None | Inputs include origin, destination, cargo, vessel/scenario parameters, and model toggles. | Explain only user-facing and validation-relevant parameters. | Exhaustive UI manual. | Input table. | `source_article_ready` |
| `4. Implementacao computacional`; `3. Metodologia` | 5. Implementation | 5.3 Route construction pipeline | Article; final report scaffold; methodology decisions | None | Pipeline builds road-only and multimodal legs with ports and provenance. | Add stepwise route-construction flow. | Full optimization/supernetwork. | Pipeline figure/table. | `source_article_ready` |
| `4. Implementacao computacional`; `5. Estrategia de validacao e benchmark` | 5. Implementation | 5.4 Data/cache layer and Supabase role | Article; Batch 002 rerun; Supabase docs if needed | None | Supabase supports cache and auditability; rerun used cached road distances. | Explain cache read/write role and 63 hits/0 misses as validation context. | Cache proves all route/provider issues impossible. | Cache/provenance table. | `source_article_ready` |
| `4. Implementacao computacional` | 5. Implementation | 5.5 Output artifacts | Article; synthesis; final report scaffold | None | Outputs include distances, costs, emissions, selected ports, warnings, and provenance. | Map outputs to academic interpretation and audit trail. | Outputs are commercial quotes or validated routes. | Output artifact table. | `source_article_ready` |
| `4. Implementacao computacional`; `5. Estrategia de validacao e benchmark` | 5. Implementation | 5.6 Reproducibility and audit trail | Article; validation run manifest; synthesis | None | Tracked artifacts and manifests support repeatability and review. | Explain artifact-based traceability without rerunning anything. | Claiming perfect reproducibility without dependency/cache caveats. | Appendix: reproducibility commands if useful. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark` | 6. Validation strategy | 6.1 Why validation is not pass/fail | Article; synthesis | `[modalshiftreview2020]`, `[shortsea2019]` as context | Validation is layered and classification-based. | Explain plausibility, dimensional consistency, provenance, benchmark, and boundary limitations. | Single validated/not validated verdict. | Evidence-layer table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark` | 6. Validation strategy | 6.2 Historical Batch 001 | Article; synthesis; Batch 001 docs if needed | None | Batch 001 is historical diagnostic evidence. | Summarize why it was retained and not overwritten. | Historical outputs as corrected final results. | Validation history table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark` | 6. Validation strategy | 6.3 Batch 001B methodology-decision layer | Article; methodology decisions; synthesis | None | Batch 001B adds auditability and classifies cases. | Explain readiness classes and decision gates. | Readiness equals headline validity. | Readiness/classification table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark`; `6. Resultados` | 6. Validation strategy | 6.4 Issue #16 sensitivity runs | Article; sensitivity results; synthesis | None | Three sensitivity rows were executed and all remain `sensitive`. | Explain why they are eligible sensitivity evidence only. | Robust baseline conclusions; exact selected-port validation. | Sensitivity-role table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark`; `6. Resultados` | 6. Validation strategy | 6.5 Batch 002 Gustavo/Costa external benchmark | Article; Batch 002 benchmark; synthesis | None; citations only if discussing literature context | External benchmark supports directional consistency for 21/21 supported OD pairs. | Explain partial comparability and workbook-boundary uncertainty. | Exact reproduction; workbook ground truth; calibrated magnitude. | Benchmark evidence table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark` | 6. Validation strategy | 6.6 Supabase/cache rerun | Article; Batch 002 rerun; synthesis | None | Cache/provider instability is unlikely to be the primary road-gap cause. | Report 63 cache hits, 0 misses, stable road mismatch. | Route/provider issues can never matter. | Cache rerun summary table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark`; `6. Resultados` | 6. Validation strategy | 6.7 Road-factor reconciliation | Article; road-factor reconciliation; synthesis | None | Diagnostic factor explains much of road-side mismatch but does not recalibrate model. | Explain diagnostic-only status and boundary caveat. | Replacing baseline road model; WTW factor validates TTW. | Road-factor diagnostic table. | `source_article_ready` |
| `5. Estrategia de validacao e benchmark` | 6. Validation strategy | 6.8 Final thesis-use categories and claim controls | Article; synthesis; citation map | None | Thesis-use categories determine safe claims and unsafe claims. | Present allowed/prohibited claims and category meanings. | Treating categories as optional wording. | Claim-control table; appendix checklist. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.1 Final case inventory and thesis-use categories | Article; final synthesis | None | No current case qualifies as `headline_candidate`. | Summarize inventory and categories without full appendix detail. | Table of robust validated baseline cases. | Case inventory summary; appendix full inventory. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.2 Internal sensitivity results | Article; synthesis; sensitivity results | None | Three sensitivity rows remain lower in modeled cost and TTW CO2e, but are `sensitive`. | Include Santos/Manaus, Manaus/Pecem, Rio Grande/Suape values and caveats. | Robust conclusions; Pecem/Fortaleza equivalence; Suape/Recife equivalence. | Sensitivity results table. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.3 Batch 002 benchmark results | Article; synthesis; Batch 002 benchmark | None | 21/21 positive supported OD pairs directionally align; magnitude mismatch remains. | Report workbook inventory and comparability status. | Exact replication; calibrated validation. | Benchmark summary table; appendix full table. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.4 Supabase/cache rerun results | Article; synthesis; rerun comparison | None | Cached rerun had 63 hits, 0 misses, and road mismatch stayed near 199.8%/149.3%. | Present previous vs rerun metrics. | Cache resolves magnitude mismatch. | Rerun comparison table. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.5 Road-factor reconciliation results | Article; synthesis; road-factor reconciliation | None | Diagnostic factor reduced mean/median road mismatch to 43.9%/19.6%. | Present formula already tracked and diagnostic-only status. | Baseline replacement; recalibration. | Road-factor summary table. | `source_article_ready` |
| `6. Resultados` | 7. Results | 7.6 Synthesis of safe numerical interpretation | Article; synthesis | None | Safe interpretation is directional and boundary-limited. | Tie sensitivity, benchmark direction, mismatch, and classifications together. | Interpretation overload; universal claims. | Short synthesis table. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.1 What the evidence supports | Article; synthesis | `[shortsea2019]`, `[modalshiftreview2020]` for cautious framing | Evidence supports an auditable framework and cautious directional interpretation. | Explain support levels by evidence layer. | Stronger claims than synthesis allows. | Evidence support table. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.2 What the evidence does not support | Article; synthesis; citation map | `[competitiveness2024]`, `[decarb2024]`, `[maritimelca2024]` as boundary contrast | Evidence does not support universal superiority, commercial rates, WTW/LCA, or calibrated validation. | Expand prohibited claims into discussion prose. | Overclaiming due to favorable directional rows. | Claim-control appendix. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.3 Why directional consistency matters but does not prove calibrated magnitude | Article; Batch 002 benchmark; synthesis | None | Directional consistency is useful, but magnitude mismatch remains. | Explain 21/21 alignment and large-gap classification. | Calibrated validation or exact reproduction. | Reference benchmark table from Results. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.4 Why the road-side benchmark gap is methodologically explainable | Article; rerun comparison; road-factor reconciliation | None | Road fuel/emission assumptions explain much of the road gap; residual remains. | Link cache rerun and diagnostic factor evidence. | Treating diagnostic as final model. | Reference road-factor table. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.5 Route, port, distance, cargo/allocation, and service-boundary implications | Article; synthesis; methodology decisions; Batch 002 benchmark | `[competitiveness2024]`, `[shortsea2019]`, `[modalshiftreview2020]` | Route and service boundaries affect interpretation. | Discuss selected/forced ports, fallback distances, allocation, and service availability. | Ignoring port/service mismatch. | None; appendix detailed blockers. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.6 Cost boundary versus commercial freight | Article; system boundary; citation map | `[competitiveness2024]`, `[modalshiftreview2020]`, `[icct2022]` as context | Model cost is not commercial freight. | Explain missing tariffs, margins, time, inventory, reliability, frequency. | Freight-rate equivalence. | Cost-boundary table from Methodology. | `source_article_ready` |
| `7. Discussao` | 8. Discussion | 8.7 Emissions boundary implications | Article; system boundary; citation map | `[decarb2024]`, `[maritimelca2024]`, `[competitiveness2024]`, `[shortsea2019]` | TTW CO2e must be kept separate from WTW/LCA/CO2-only evidence. | Explain comparison limits and future expansion path. | Boundary mixing. | Emissions-boundary table from Methodology. | `source_article_ready` |
| `7. Discussao`; `9. Conclusoes` | 8. Discussion | 8.8 Engineering value of an auditable framework | Article; synthesis; final report scaffold | None | Value lies in traceability, classification, and defensible assumptions. | Tie route-aware computation to naval engineering decision support. | Claiming operational deployment completeness. | None. | `source_article_ready` |
| `8. Limitacoes` | 9. Limitations | 9.1 Environmental boundary limitations | Article; system boundary; citation map | `[decarb2024]`, `[maritimelca2024]`, `[competitiveness2024]` | Environmental boundary is operational TTW CO2e. | List excluded upstream/lifecycle components. | WTW/LCA conclusions. | Limitation-to-future-work table. | `source_article_ready` |
| `8. Limitacoes` | 9. Limitations | 9.2 Cost-boundary limitations | Article; system boundary; citation map | `[competitiveness2024]`, `[modalshiftreview2020]`, `[icct2022]` | Costs are model estimates, not commercial freight rates. | List missing commercial cost categories. | Freight quotes or market rates. | Limitation-to-future-work table. | `source_article_ready` |
| `8. Limitacoes`; `5. Estrategia de validacao e benchmark` | 9. Limitations | 9.3 Route, port, and maritime-distance limitations | Article; synthesis; methodology decisions | `[shortsea2019]`, `[competitiveness2024]` | Fallback distances, selected-port gaps, and alternate-port sensitivities limit conclusions. | Explain same-port, Fortaleza/Recife reference gaps, Pecem/Suape limitations. | Silent port substitution. | Appendix blocked/excluded cases. | `source_article_ready` |
| `8. Limitacoes`; `2. Posicionamento na literatura` | 9. Limitations | 9.4 Service availability, frequency, and supernetwork limitations | Article; citation map | `[competitiveness2024]`, `[modalshiftreview2020]` | CabotageLens does not model schedules, frequency, service availability, or full supernetwork. | Explain real modal decision factors outside scope. | Full network optimization claims. | Limitation-to-future-work table. | `source_article_ready` |
| `8. Limitacoes`; `6. Resultados` | 9. Limitations | 9.5 Gustavo/Costa benchmark comparability limitations | Article; Batch 002 benchmark; synthesis | None | Workbook is external benchmark, not ground truth, and not fully reconciled. | Discuss cargo, allocation, ports, routes, boundaries, and skipped cells. | Exact reproduction; calibrated validation. | Appendix full Batch 002 table. | `source_article_ready` |
| `8. Limitacoes` | 9. Limitations | 9.6 Sensitivity-only and not-comparable evidence limitations | Article; synthesis; sensitivity results | None | Sensitive and not-comparable rows cannot support headline conclusions. | Explain three sensitivity rows and 15 skipped matrix cells. | Promoting sensitivity or skipped rows. | Claim-control appendix. | `source_article_ready` |
| `8. Limitacoes`; `4. Implementacao computacional` | 9. Limitations | 9.7 Implementation/data limitations | Article; port ops model; rerun comparison | `[berth2009]`, `[shipops2022]`, `[berthairquality2010]` only as context/future work | Implementation and data are bounded by tracked artifacts, caches, placeholders, and missing source evidence. | Explain port-ops placeholders, cache dependence, data gaps, and audit trail limits. | Treating placeholders as calibrated local factors. | Implementation/data limitation table. | `source_article_ready` |
| `9. Conclusoes` | 10. Conclusions and future work | 10.1 Main conclusion | Article; synthesis | None | Main conclusion is the defensible framework contribution plus cautious directional evidence. | Condense without adding new claims. | Universal cabotage superiority. | None. | `source_article_ready` |
| `9. Conclusoes` | 10. Conclusions and future work | 10.2 Methodological contribution | Article; synthesis; final report scaffold | None | Contribution is auditable, reproducible, boundary-explicit comparison. | Tie Batch 001B/002 evidence controls to methodology. | Calibrated validation. | None. | `source_article_ready` |
| `9. Conclusoes`; `6. Resultados` | 10. Conclusions and future work | 10.3 Evidence-based findings | Article; synthesis | None | Findings are named, classified, and boundary-limited. | Summarize sensitivity rows, 21/21 directional alignment, road-factor diagnostic. | New numbers or stronger result classes. | None; reference Results tables. | `source_article_ready` |
| `9. Conclusoes`; `7. Discussao` | 10. Conclusions and future work | 10.4 Practical/engineering implications | Article; synthesis; citation map | `[competitiveness2024]`, `[modalshiftreview2020]` as broader context | Practical value is traceable comparison and assumption visibility. | Explain how framework supports academic/engineering decisions without replacing commercial planning. | Operational deployment completeness. | None. | `source_article_ready` |
| `10. Trabalhos futuros`; `8. Limitacoes` | 10. Conclusions and future work | 10.5 Future work | Article; final report scaffold; citation map | `[decarb2024]`, `[maritimelca2024]`, `[competitiveness2024]`, `[modalshiftreview2020]`, `[isoemission2019]`, `[berth2009]`, `[shipops2022]` as future/context only | Future work targets the boundaries that currently limit stronger claims. | Include WTW/LCA, Gustavo/Costa reconciliation, maritime distance, commercial freight, supernetwork, expanded validation. | Presenting future work as already implemented. | Future-work table. | `source_article_ready` |
| `Resumo`; all article body sections | Pre-textual | Resumo/abstract | Article; final report after body stabilization | Citation placeholders usually not needed in abstract | Abstract must reflect final method, evidence, and conclusion. | Draft after body chapters are stable. | Promising unsupported results. | Pre-textual item for issue #26. | `not_started` |
| `12. Referencias e artefatos` | References | References and formatting | Article; citation map; references files | Only approved placeholders from citation map | Citation placeholders must be formatted without invented metadata. | Handle in issue #26. | New citations; invented metadata. | Final reference list. | `not_started` |
| `11. Tabelas de apoio` and validation artifacts | Appendices | Appendices | Article; synthesis; validation artifacts | As needed from citation map | Appendix carries detail that would overload main narrative. | Detailed case inventory, validation tables, Batch 002 tables, reconciliation table, claim checklist, reproducibility commands. | Putting appendix-level detail in main narrative unnecessarily. | Appendices A-N as needed. | `not_started` |

## 6. Recommended writing order

Recommended order:

1. System boundary and methodology.
2. Computational implementation.
3. Validation/benchmark/evidence-classification strategy.
4. Results.
5. Discussion.
6. Limitations.
7. Conclusions and future work.
8. Literature review and positioning.
9. Objectives and contribution.
10. Introduction.
11. Resumo/abstract.
12. References and formatting.

Rationale:

- Methodology must be drafted first because it controls the meaning of every result.
- Implementation comes early because reproducibility and provenance are part of the contribution, not decoration.
- Validation strategy should precede Results so the reader understands why cases are classified as sensitivity-only, benchmark-limited, excluded, or not-comparable.
- Results should be drafted before Discussion to keep observed numbers separate from interpretation.
- Limitations should follow Discussion so they can be precise instead of generic.
- Conclusions should be written only after the evidence boundary is clear.
- Literature review can be finalized after methodology/results because every citation must serve a specific method, limitation, or positioning role.
- Objectives and Introduction should be finalized late so they do not promise stronger claims than the final evidence supports.
- Resumo and Abstract should be finalized last because they must reflect the final method, evidence, and conclusion rather than promise something the results do not support.
- References and formatting belong to the final submission pass, mainly issue #26.

## 7. Subsection drafting prompt template

Use this template for future coding-agent tasks. Fill in the placeholders before running the task.

```text
You are working on the pennylanesccp/cabotage-lens repository.

Work directly on main. Do not create a branch. Do not open a PR.

Task:
Draft exactly one final TF report subsection.

Target subsection:
<target subsection number and title>

Target file:
<target file path>

Source article section:
<exact source article section from docs/tf_technical_article_draft.md>

Source artifacts:
<list exact source artifact paths>

Allowed claims:
<list allowed claims for this subsection>

Prohibited claims:
<list prohibited claims for this subsection>

Allowed citation placeholders:
<list citation placeholders allowed by docs/tf_literature_citation_map.md, or "none">

Expected length:
<paragraph/word target>

Validation checklist:
- Confirm the subsection names its source article section in the work summary.
- Confirm the subsection expands from the article section, not from scratch.
- Confirm source traceability is preserved.
- Confirm no other subsection was written.
- Confirm the full report was not rewritten.
- Confirm no new results, citations, assumptions, routes, ports, distances, formulas, factors, model parameters, workbook values, or metadata were introduced.
- Confirm TTW, WTW, LCA, CO2, and CO2e boundaries remain explicit where relevant.
- Confirm model cost estimates are not described as commercial freight rates.
- Confirm sensitive, benchmark-mismatched, not-comparable, blocked, excluded, reference-needed, and historical-diagnostic evidence is not promoted to robust evidence.
- Confirm any citation placeholders used are allowed by docs/tf_literature_citation_map.md.
- Confirm what was changed and which source article section was used.

Hard constraints:
- Do not write any other subsection.
- Do not rewrite the full report.
- Expand from the article section, not from scratch.
- Preserve source traceability.
- Report what was changed and which source article section was used.
```

## 8. Handoff

Recommended first subsection to draft after this plan is complete:

`4.1 Functional unit and cargo basis`

Reason:

This subsection is foundational. It controls interpretation of the article, the final TF method, the sensitivity rows, and the Batch 002 benchmark. It also reduces the risk of later result overclaiming by fixing the cargo basis, shipment basis, normalization options, and benchmark comparability caveats before any numerical results are drafted.
