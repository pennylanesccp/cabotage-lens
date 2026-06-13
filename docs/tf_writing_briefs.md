# TF Writing Briefs

## 1. Purpose

This document is a section-by-section writing guide for the final undergraduate thesis/report on CabotageLens. It helps the author decide what to write, what evidence is needed, which methodology notes support each section, what claims should be avoided, and which risks or methodology debts may appear while drafting.

This is a planning document only. It does not add results, run calculations, change data, or define final coefficients.

The guide is based on the available TF planning and methodology documents:

- `docs/tf_document_structure.md`
- `docs/tf_system_boundary.md`
- `docs/tf_data_reliability_inventory.md`
- `docs/tf_assumptions_and_approximations.md`
- `docs/tf_validation_plan.md`
- `docs/tf_sensitivity_analysis_plan.md`
- `docs/tf_result_classification_rules.md`
- `docs/methodology_audit.md`
- `docs/mrv_container_efficiency.md`
- `docs/hoteling_model.md`
- `docs/port_ops_model.md`
- `docs/costa_allocation_validation.md`
- `docs/tf.tex`

These documents should be read together as the current TF planning set for structure, boundary, data reliability, assumptions, validation, sensitivity, classification, and writing guidance.

## 2. Section-by-section briefs

### Introduction

**Purpose**

Introduce the research problem: comparing Brazilian road-only freight with road-cabotage-road alternatives using a reproducible model for costs, fuel, emissions, and route structure.

**Key questions**

- Why is road versus cabotage comparison relevant in Brazil?
- Why is a door-to-door comparison necessary instead of comparing only truck versus ship?
- What is the specific contribution of CabotageLens?
- What is the scope of the TF: model, software tool, methodology, validation plan, or final empirical results?

**Required evidence**

- Context on Brazilian freight dependence on road transport.
- Cabotage relevance and limitations in Brazil.
- Project objective and unit of comparison.
- Clear statement that the tool compares complete chains: road-only versus pre-carriage, sea leg, and on-carriage.
- If used, concise summary of the ANTAQ+MRV route-intensity contribution already described in `docs/tf.tex`.

**Methodology risks**

- Do not claim that cabotage is always better.
- Do not imply full freight-rate accuracy if costs are simplified energy/operations costs.
- Do not imply lifecycle emissions if the current boundary is tank-to-wheel.
- Avoid introducing results before validation and sensitivity framing are defined.

**Writing notes**

State the research problem as an applied modeling question: how to compare alternatives transparently and reproducibly. Keep claims narrow: the thesis builds and documents a defensible comparison framework, not a universal answer for all Brazilian corridors.

### Literature review

**Purpose**

Position the project in relation to modal comparison, cabotage competitiveness, maritime emissions, MRV data, port operations, hoteling, and fuel/emissions boundaries.

**Key questions**

- What does the literature say about short-sea/cabotage emissions and competitiveness?
- Why does route, cargo, and service context matter?
- Why are observed vessel or route indicators preferable to generic average factors?
- What are the known limitations of tank-to-wheel versus well-to-wake comparison?

**Required evidence**

- References already listed in `docs/methodology_audit.md` and `docs/references.bib`.
- Literature supporting Brazilian cabotage context and supernetwork/service logic.
- Literature supporting EU MRV use for maritime efficiency.
- Literature or references supporting hoteling and port operations as relevant phases.
- Literature explaining why full lifecycle fuel analysis requires a broader boundary.

**Methodology risks**

- Avoid presenting literature ranges as direct validation unless boundaries match.
- Avoid mixing TTW, WTW, and LCA claims without labeling.
- Avoid using port or maritime references outside their scope, such as applying a generic vessel factor to every Brazilian corridor without caveat.

**Writing notes**

Use the literature review to justify the model structure: door-to-door comparison, route-specific treatment, observed-data preference, and explicit limitations. Keep operational, economic, and emissions evidence separate when source boundaries differ.

### Methodology

**Purpose**

Define the model boundary, inputs, assumptions, calculations, route construction, emission/cost treatment, validation logic, sensitivity logic, and result classification rules.

**Key questions**

- What alternatives are compared?
- What is included in the road-only chain?
- What is included in the multimodal chain?
- How are road distances, port selection, sea distances, fuel, emissions, and costs computed?
- Which assumptions are high-impact?
- How will results be classified as robust, sensitive, inconclusive, or invalid?

**Required evidence**

- System flow from `docs/tf.tex`: geocoding, nearest ports, road routing, sea matrix, fuel/emissions/cost evaluation, persistence.
- Assumption inventory from `docs/tf_assumptions_and_approximations.md`.
- Validation plan from `docs/tf_validation_plan.md`.
- Sensitivity plan from `docs/tf_sensitivity_analysis_plan.md`.
- Classification rules from `docs/tf_result_classification_rules.md`.
- Unit definitions: km, nautical mile, tonnes, TEU, L, kg fuel, kg CO2e, BRL.

**Methodology risks**

- Do not hide fallback paths such as class-level vessel intensity, fallback maritime distance, or default fuel prices.
- Do not present nearest-port selection as a full service-network model.
- Do not double count hoteling when transport-work intensity already represents operational fuel.
- Do not use unexplained cost outputs as full logistics cost.

**Writing notes**

This section should be explicit and auditable. Use tables for assumptions, boundaries, and classification rules. Make clear that validation and sensitivity analysis are part of interpretation, not optional extras.

### Implementation / computational tool

**Purpose**

Explain how the methodology is implemented in the repository without turning the thesis into a code walkthrough.

**Key questions**

- What are the main software layers?
- Which modules handle routing, multimodal evaluation, fuel/emissions, costs, and persistence?
- How does the Streamlit app relate to CLI scripts and reusable modules?
- How does persistence/caching support reproducibility?

**Required evidence**

- Repository structure: `app/`, `scripts/`, `modules/`, `data/`, `supabase/`, `references/`.
- `docs/supabase_postgres.md` for persistence context if needed.
- Current implementation notes from `docs/tf.tex`.
- Runtime assumptions from `docs/tf_assumptions_and_approximations.md`.
- Evidence that Supabase Postgres is the durable backend and Storage is archival/file-log sink where configured.

**Methodology risks**

- Avoid excessive code detail that distracts from methodology.
- Avoid claiming every output is reproducible unless data artifact versions, code version, inputs, route cache status, and fallback flags are recorded.
- Avoid treating caches as truth; they improve repeatability but may preserve older provider responses.

**Writing notes**

Frame the tool as a research instrument. Explain module boundaries at a high level: geometry construction, fuel/emissions/cost evaluation, persistence, and interface/orchestration. Include a simple workflow diagram if the final document format allows it.

### Case study / scenarios

**Purpose**

Define the OD pairs, port pairs, cargo assumptions, scenario boundaries, and validation/sensitivity sample used in the thesis.

**Key questions**

- Which OD pairs or corridors are included, and why?
- What cargo unit is used: tonnes, TEU, or a benchmark container?
- Are cases selected for geography, data availability, benchmark comparability, or edge-case testing?
- Which cases are main evidence and which are stress tests or out-of-scope examples?

**Required evidence**

- Candidate OD and port-pair samples from `docs/tf_validation_plan.md`.
- Cargo mass, TEU, load factor, and boundary assumptions from current model inputs and `docs/tf_sensitivity_analysis_plan.md`.
- Route plausibility checks and validation status.
- Clear indication of whether each route uses observed route intensity, corridor aggregation, class fallback, or another fallback.

**Methodology risks**

- Do not cherry-pick only cabotage-favorable corridors without explaining selection.
- Do not mix validation samples, sensitivity samples, and final case-study samples without labeling.
- Do not include routes whose operational logic is invalid unless clearly marked as out-of-scope or stress tests.

**Writing notes**

Use a case-study table with OD pair, cargo assumption, selected ports, distance source, maritime intensity source, validation status, and purpose of inclusion. Separate "main thesis cases" from "edge-case checks".

### Results

**Purpose**

Present model outputs and classifications without overstating precision.

**Key questions**

- What are the base cost and emissions differences?
- What are the road-only, pre-carriage, sea, and on-carriage distances?
- Which results are robust, sensitive, inconclusive, or out-of-scope?
- Which results differ for cost versus emissions?

**Required evidence**

- Final model outputs, once generated.
- Validation status for each route.
- Sensitivity results for high-priority parameters.
- Classification table based on `docs/tf_result_classification_rules.md`.
- Units and boundaries for every table: BRL, kg CO2e, km, nm, tonnes, TEU, TTW, cost boundary.

**Methodology risks**

- Do not report too many decimal places for planning-level estimates.
- Do not rank alternatives without validation and sensitivity context.
- Do not average invalid or out-of-scope cases into aggregate conclusions.
- Do not combine cost and emissions into one winner when they disagree unless an explicit decision rule is defined.

**Writing notes**

Put headline findings in classification language, not just numerical language. For example: "robust emissions advantage but cost-sensitive" is more defensible than "cabotage is better." Include source/fallback flags in result tables where possible.

### Discussion

**Purpose**

Interpret what the results mean for modal comparison, methodology, and engineering decision-making.

**Key questions**

- Which corridors show robust evidence?
- Which results are sensitive to fuel price, fuel consumption, route distance, hoteling, backhaul, or cost boundary?
- What does the model reveal about when cabotage is promising or weak?
- How do findings compare with literature or benchmark workbook evidence?

**Required evidence**

- Classified results from the Results section.
- Sensitivity drivers from `docs/tf_sensitivity_analysis_plan.md`.
- Validation and failure handling from `docs/tf_validation_plan.md`.
- Literature and benchmark context from `docs/methodology_audit.md`, `docs/costa_allocation_validation.md`, and `docs/tf.tex`.

**Methodology risks**

- Avoid converting sensitive findings into broad policy claims.
- Avoid treating benchmark agreement as final validation if boundaries differ.
- Avoid making operational claims about service availability unless supported by schedule or network evidence.

**Writing notes**

Structure the discussion around patterns: robust corridors, sensitive corridors, inconclusive corridors, and invalid/out-of-scope cases. Explain why results change, not only that they change.

### Limitations

**Purpose**

Make the model boundaries, unresolved assumptions, data gaps, and threats to validity explicit.

**Key questions**

- Which assumptions most affect conclusions?
- Which data sources are partial or uncertain?
- Which model components are simplified?
- Which claims should the thesis not make?

**Required evidence**

- High-impact assumptions and methodology debts from `docs/tf_assumptions_and_approximations.md`.
- Validation failures or pending checks from `docs/tf_validation_plan.md`.
- Sensitivity parameters requiring source verification from `docs/tf_sensitivity_analysis_plan.md`.
- Out-of-scope criteria from `docs/tf_result_classification_rules.md`.

**Methodology risks**

- Do not bury limitations after strong claims.
- Do not imply limitations are minor if they affect route feasibility, cost boundary, or emissions scope.
- Do not present missing data as if it were validated by model output.

**Writing notes**

Use direct limitation categories: data coverage, route logic, fuel/emissions factors, cost boundary, port operations, hoteling, backhaul, lifecycle boundary, and reproducibility. For each, state whether it affects cost, emissions, route plausibility, or generalization.

### Conclusion

**Purpose**

Summarize the thesis contribution and the defensible findings within the validated boundary.

**Key questions**

- What did the project build?
- What methodological improvement does it provide?
- Which conclusions are robust, sensitive, inconclusive, or invalid?
- What should a reader take away about road versus cabotage comparison?

**Required evidence**

- Final classified result table.
- Key validation and sensitivity outcomes.
- Clear scope statement: Brazilian freight comparison, road-only versus road-cabotage-road, direct operational emissions, and simplified cost boundary unless expanded.
- Statement of contribution: reproducible, auditable, route-aware methodology.

**Methodology risks**

- Do not state that cabotage is categorically superior.
- Do not imply exact prediction of real freight rates or actual carrier operations.
- Do not generalize beyond the case-study and validated data coverage.

**Writing notes**

End with a balanced conclusion: the tool improves transparency and evidence quality, but conclusions depend on corridor, data quality, operating boundary, and sensitivity behavior.

### Future work

**Purpose**

Identify realistic extensions that address known methodology debts and improve decision usefulness.

**Key questions**

- What model components most need better data?
- What validations or sensitivity analyses should be completed next?
- What features would move the model closer to operational freight decision-making?
- What would be needed for well-to-wake or full logistics-cost analysis?

**Required evidence**

- Methodology debts from assumptions, validation, sensitivity, and classification docs.
- Future-work items from `docs/methodology_audit.md`, `docs/hoteling_model.md`, and `docs/port_ops_model.md`.
- Known gaps: service network, port feasibility, inland waterways, backhaul, non-fuel costs, shore power, reefers, electricity factors, WTW factors, multi-year ANTAQ/MRV coverage.

**Methodology risks**

- Do not promise future work as if it were implemented.
- Do not frame missing features as already solved by current outputs.
- Avoid vague future work; tie each item to a specific limitation or validation gap.

**Writing notes**

Group future work by theme: data coverage, route/service realism, emissions boundary, cost boundary, port operations, software reproducibility, and validation automation.

## 3. Cross-document map

| TF section | Supporting docs | Evidence needed | Main risk |
| --- | --- | --- | --- |
| Introduction | `docs/tf.tex`, `docs/tf_assumptions_and_approximations.md` | Problem framing, research objective, model boundary summary | Overclaiming cabotage advantage before evidence |
| Literature review | `docs/methodology_audit.md`, `docs/references.bib`, `docs/costa_allocation_validation.md` | Cabotage, MRV, emissions, port operations, cost-boundary literature | Mixing source boundaries or unsupported references |
| Methodology | `docs/tf_assumptions_and_approximations.md`, `docs/tf_validation_plan.md`, `docs/tf_sensitivity_analysis_plan.md`, `docs/tf_result_classification_rules.md` | Equations, assumptions, validation/sensitivity/classification rules | Hiding fallbacks or uncertainty |
| Implementation / computational tool | `docs/tf.tex`, `docs/supabase_postgres.md`, `docs/mrv_container_efficiency.md`, `docs/hoteling_model.md`, `docs/port_ops_model.md` | Repo architecture, data artifacts, runtime flow, persistence | Turning thesis into code walkthrough or overstating reproducibility |
| Case study / scenarios | `docs/tf_validation_plan.md`, `docs/tf_sensitivity_analysis_plan.md`, `docs/tf_result_classification_rules.md` | OD sample, cargo assumptions, route/port selection, scenario definitions | Cherry-picking or including implausible routes |
| Results | `docs/tf_result_classification_rules.md`, `docs/tf_validation_plan.md`, `docs/tf_sensitivity_analysis_plan.md` | Base outputs, validation status, sensitivity behavior, classifications | Reporting numbers without uncertainty context |
| Discussion | `docs/tf_result_classification_rules.md`, `docs/costa_allocation_validation.md`, `docs/methodology_audit.md` | Pattern interpretation, benchmark/literature comparison, sensitivity drivers | Treating sensitive results as robust |
| Limitations | `docs/tf_assumptions_and_approximations.md`, `docs/tf_validation_plan.md`, `docs/tf_sensitivity_analysis_plan.md` | Data gaps, boundary limits, validation failures, source-verification needs | Understating limitations |
| Conclusion | `docs/tf_result_classification_rules.md`, `docs/tf.tex` | Final classified findings and contribution statement | Generalizing beyond validated scope |
| Future work | `docs/methodology_audit.md`, `docs/port_ops_model.md`, `docs/hoteling_model.md`, `docs/tf_assumptions_and_approximations.md` | Methodology debts and concrete extensions | Presenting future work as current capability |

## 4. Writing principles

- Distinguish observed data from modeled outputs. ANTAQ/MRV records, reference workbooks, processed artifacts, and model estimates are not the same type of evidence.
- Do not overclaim precision. Use appropriate rounding and avoid false certainty for planning-level estimates.
- Avoid saying cabotage is always better. Classify findings by corridor and boundary.
- Classify results as robust, sensitive, inconclusive, or out-of-scope according to `docs/tf_result_classification_rules.md`.
- Make assumptions and limitations explicit before interpreting results.
- Preserve units and dimensional consistency. Label km, nautical miles, tonnes, TEU, L, kg fuel, kg CO2e, BRL, kg CO2e/tkm, and BRL/tkm.
- Keep cost and emissions conclusions separate unless a combined decision rule is explicitly defined.
- State whether cost means fuel-only, energy plus port operations, or a broader logistics-cost proxy.
- State whether emissions mean tank-to-wheel direct emissions or a broader lifecycle boundary.
- Report fallback and quality flags where they affect interpretation: maritime distance source, fuel-intensity source, validation status, hoteling treatment, port-ops treatment, and route plausibility.
- Treat validation and sensitivity analysis as evidence filters, not decorative appendices.
- Mark unresolved source tracing, parameter ranges, and operational feasibility issues as methodology debt rather than filling gaps with invented certainty.
