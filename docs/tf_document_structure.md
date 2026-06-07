# Proposed TF Document Structure

This file defines the proposed final structure for the undergraduate thesis/report
supported by this repository. It is a planning document, not the final text.

The report should present the project as a reproducible logistics modeling study
for comparing road-only freight with multimodal road-cabotage-road freight in
Brazil. The structure below follows the repository's current architecture:
thin app/script orchestration, reusable modeling logic in `modules/`, versioned
inputs under `data/`, processed cabotage artifacts, and auditable persistence of
routing and scenario results.

## Working Title

Comparative Assessment of Cost and Carbon Emissions for Road and Cabotage Freight
Corridors in Brazil

## Core Research Question

Under the model assumptions implemented in this repository, when does a
road-cabotage-road transport chain reduce greenhouse gas emissions and/or
logistics cost compared with a road-only route for Brazilian freight corridors?

## Secondary Questions

- Which origin-destination corridors show the largest modeled emissions savings?
- Which corridors show cost savings, cost penalties, or trade-offs between cost
  and emissions?
- How sensitive are the results to cargo mass, diesel price, marine fuel price,
  vessel class, hoteling assumptions, and port selection?
- Which methodology limitations are most important when interpreting the results?

## Proposed Final Structure

### Front Matter

Purpose:
Identify the work and make the document navigable.

Expected content:
- Cover page.
- Abstract in Portuguese.
- Abstract in English, if required by the institution.
- List of figures.
- List of tables.
- List of abbreviations and symbols.

Robustness checkpoints:
- Use the same terminology throughout: origin-destination pair, road-only route,
  multimodal route, road leg, sea leg, port hoteling, emissions, cost.
- Define all units before results appear.

Writing rules:
- Keep the abstract result-oriented: problem, method, data, main findings,
  limitations.
- Do not introduce new methods or caveats only in the abstract.

### 1. Introduction

Purpose:
Explain the logistics and sustainability problem, why Brazilian cabotage is a
relevant modal-shift alternative, and what the thesis contributes.

Expected content:
- Context of freight transport in Brazil and the dominance of road transport.
- Motivation for comparing road-only and road-cabotage-road chains.
- Environmental and economic relevance of emissions and cost indicators.
- Research question and secondary questions.
- Scope boundaries: containerized/general freight representation, Brazil-focused
  corridors, deterministic scenario modeling.
- Short description of the computational artifact in this repository.

Robustness checkpoints:
- Separate policy motivation from modeled evidence.
- State that the model compares scenarios under explicit assumptions, not observed
  market behavior.
- State whether emissions are tank-to-wake/tank-to-wheel only, unless the method
  is later extended.

Methodology debts to track:
- Need final alignment between the text and the exact emissions scope implemented
  at thesis freeze time.
- Need final wording for cargo type and whether the model is best described as
  containerized freight, generic cargo mass, or TEU-proxy analysis.

Writing rules:
- Avoid claiming cabotage is always cleaner or cheaper.
- Use "modeled reduction" or "estimated reduction" instead of absolute claims.

### 2. Literature and Technical Background

Purpose:
Position the thesis in logistics, modal shift, freight emissions accounting, and
maritime/road fuel modeling literature.

Expected content:
- Brazilian freight matrix and modal imbalance.
- Cabotage and short sea shipping as alternatives to long-haul trucking.
- Emissions accounting concepts for freight transport.
- Activity-based modeling: distance, fuel use, emissions factors, and cost factors.
- Road routing and heavy-goods route estimation.
- Maritime fuel use, vessel classes, sea distance, and port hoteling.
- Prior work on cost-emissions trade-offs in freight corridors.

Robustness checkpoints:
- Distinguish empirical data sources from model parameters.
- Identify which literature values become direct model inputs.
- Explain why deterministic scenario modeling is acceptable for a first-order
  comparative study.

Methodology debts to track:
- Need source-quality ranking for each parameter family: regulator data, public
  operational data, literature, calibrated assumption.
- Need final citation list for ANTAQ, ANTT, ANP, ORS, EU MRV, EMEP/EEA, and any
  emissions-factor references used.

Writing rules:
- Do not turn the chapter into a broad sustainability essay; keep it tied to
  corridor comparison and methodology choices.
- Every cited method should later connect to a data source, formula, or limitation.

### 3. Data Sources and Input Preparation

Purpose:
Document all input data used by the model and how raw/reference inputs become
runtime-ready artifacts.

Expected content:
- Repository data layout and distinction between raw, processed, and runtime
  reference files.
- Origin-destination scenario inputs.
- Port metadata and port alias/normalization rules.
- Sea distance matrix and coastline-factor fallback logic.
- Road routing inputs from OpenRouteService.
- Truck presets and road consumption assumptions.
- Vessel classes and MRV-derived fuel efficiency artifacts.
- Hoteling assumptions and processed hoteling rates.
- Fuel prices and emissions factors.
- Supabase/Postgres persistence expectations if the final runtime uses the
  project-level durable backend.

Robustness checkpoints:
- For each data source, record: source institution, file/table name, temporal
  coverage, units, preprocessing script or loader, and where it is used.
- Confirm processed artifacts are deterministic for a fixed raw dataset and script
  arguments.
- Confirm units are converted only once and named clearly in code and tables.
- Confirm no secret, credential, or private data is required to reproduce the
  documented calculations.

Methodology debts to track:
- Need a final data inventory table with one row per input artifact.
- Need to reconcile any README or implementation drift around persistence backend
  before final submission.
- Need final decision on whether to document both `data/sea_matrix.json` and
  `data/processed/cabotage_data/sea_matrix.json`, or only the runtime source.

Writing rules:
- Prefer tables for input inventories.
- Use code paths only as traceability references; explain the data in academic
  language first.

### 4. Methodology

Purpose:
Give a reproducible, auditable description of how each scenario is computed.

Expected content:
- Scenario definition:
  - Inputs: origin, destination, cargo mass, selected parameters.
  - Outputs: distance, fuel, emissions, cost, and comparison indicators.
- Route construction:
  - Road-only chain: origin to destination by truck.
  - Multimodal chain: origin to origin port by truck, sea leg between ports,
    destination port to destination by truck.
- Road model:
  - ORS geocoding/routing.
  - Heavy-goods profile.
  - Cache/reuse behavior.
  - Truck capacity and trip count.
  - Loaded and empty/backhaul treatment.
  - Diesel consumption, emissions, and cost formulas.
- Maritime model:
  - Port-pair sea distance.
  - Vessel class selection.
  - MRV-derived sea fuel rate or fuel-per-distance assumptions.
  - Hoteling fuel and port-call assumptions.
  - Marine fuel emissions and cost formulas.
- Aggregation:
  - Leg-level totals.
  - Route-level totals.
  - Difference and percentage-difference indicators.
- Reproducibility:
  - Versioned code.
  - Versioned inputs.
  - Database-backed route/result reuse.
  - Logs for diagnostic traceability.

Robustness checkpoints:
- Every formula must include units for each variable.
- Every parameter must map to a data source, default value, or documented
  assumption.
- The road and multimodal scenarios must use comparable cargo mass and price
  assumptions.
- Cached road distances must be treated as model inputs once persisted.
- Missing sea distances or ports must have documented fallback or failure behavior.
- Sensitivity parameters must be clearly separated from baseline parameters.

Methodology debts to track:
- Need final formula audit against the exact implementation used for results.
- Need final confirmation of the active persistence layer and schema names.
- Need final statement on whether CH4 and N2O are excluded or included.
- Need final statement on terminal yard equipment: explicitly modeled, embedded in
  hoteling, or out of scope.
- Need final statement on volume constraints and cargo mix.

Writing rules:
- Write formulas in a compact, numbered format.
- Keep implementation paths in parentheses after the conceptual explanation.
- Do not describe deprecated code paths.

### 5. Computational Implementation

Purpose:
Explain the software artifact enough for reproducibility without replacing the
methodology chapter with code documentation.

Expected content:
- Repository architecture:
  - `app/` and `scripts/` as orchestration layers.
  - `modules/` as domain logic.
  - `data/` as versioned inputs and processed artifacts.
  - `supabase/` migrations if schema changes support the final run.
  - `docs/` as method notes and planning material.
- Main execution workflows:
  - Single comparison.
  - Bulk comparison.
  - Streamlit app, if used for demonstration or exploration.
- Logging and diagnostics.
- Idempotence and cache behavior.
- Configuration and required secrets, without exposing actual secret values.

Robustness checkpoints:
- Confirm that commands shown in the thesis run from a clean environment with safe
  placeholder secrets.
- Confirm app/script behavior is consistent with the methodology chapter.
- Confirm rerunning a scenario does not silently change results unless inputs,
  code, or cache/database state changed.

Methodology debts to track:
- Need a final reproducibility appendix with exact commands used for the thesis
  result freeze.
- Need a final schema/reference section for persisted result tables.

Writing rules:
- Keep code references minimal and purposeful.
- Do not include secrets, local absolute paths, or machine-specific configuration.

### 6. Experimental Design

Purpose:
Define the baseline scenarios, comparison groups, and sensitivity analyses before
presenting results.

Expected content:
- Baseline corridor set and rationale.
- Baseline cargo mass and vehicle/vessel assumptions.
- Baseline price assumptions.
- Baseline port selection assumptions.
- Baseline hoteling assumptions.
- Sensitivity analyses:
  - Cargo mass.
  - Diesel price.
  - Marine fuel price.
  - Vessel class/fuel efficiency.
  - Hoteling hours and port calls.
  - Empty backhaul share.
  - Alternative ports, where relevant.
- Exclusion criteria for invalid or incomplete scenarios.

Robustness checkpoints:
- Define the baseline before seeing or discussing results.
- Keep one scenario identifier per modeled run.
- Preserve failed or excluded scenario counts in logs/tables.
- Avoid mixing calibration runs with final comparison runs.

Methodology debts to track:
- Need final corridor list and justification.
- Need final decision on whether the thesis emphasizes all Brazilian capitals, a
  smaller corridor sample, or a policy-relevant subset.
- Need final minimum output table schema for each run.

Writing rules:
- Use scenario tables instead of prose lists where possible.
- Label sensitivity results as sensitivity results, not alternative baselines.

### 7. Results

Purpose:
Present modeled outputs clearly and without overclaiming causality.

Expected content:
- Baseline road-only vs multimodal totals by corridor.
- Emissions comparison:
  - Absolute difference.
  - Percentage difference.
  - Emissions intensity, if available.
- Cost comparison:
  - Absolute difference.
  - Percentage difference.
  - Cost per tonne or per route, if available.
- Distance and leg composition:
  - Road distance avoided.
  - Sea distance added.
  - Port/hoteling contribution.
- Corridor ranking:
  - Largest emissions savings.
  - Largest cost savings.
  - Corridors with trade-offs.
- Sensitivity results.

Robustness checkpoints:
- Confirm totals equal the sum of leg-level results.
- Confirm signs are consistent: multimodal minus road-only, or road-only minus
  multimodal, but never both without explicit labels.
- Confirm percentage changes use a documented denominator.
- Include uncertainty/limitation language for all parameter-sensitive findings.

Methodology debts to track:
- Need final figure/table numbering plan.
- Need final reproducibility hash or run metadata for the results freeze.
- Need final decision on map/heatmap inclusion.

Writing rules:
- Lead with the result pattern, then quantify it.
- Do not bury units in captions only.
- Avoid saying "optimal" unless an optimization model was actually run.

### 8. Discussion

Purpose:
Interpret results in relation to logistics, decarbonization, cost trade-offs, and
model limitations.

Expected content:
- Why certain corridors favor cabotage.
- Why certain corridors remain road-favorable.
- Emissions vs cost trade-offs.
- Influence of port access distances.
- Influence of hoteling and vessel efficiency assumptions.
- Practical interpretation for logistics planning and public policy.
- Comparison with expectations from literature.

Robustness checkpoints:
- Tie each interpretation back to a result table or sensitivity result.
- Separate model result, explanation, and policy implication.
- State where the model is directional rather than decision-grade.

Methodology debts to track:
- Need final discussion of external validity: which corridors or cargo types the
  findings should not be generalized to.
- Need final policy caveats around service frequency, transit time, capacity, and
  operational reliability if these remain outside the model.

Writing rules:
- Use cautious verbs: suggests, indicates, is consistent with.
- Do not present unmodeled constraints as if they were tested.

### 9. Limitations and Methodology Debts

Purpose:
Make the boundaries of the work explicit and provide a transparent backlog for
future improvement.

Expected content:
- Emissions scope limitations:
  - Tank-to-wheel/tank-to-wake vs well-to-wheel/well-to-wake.
  - CO2-only vs full CO2e, if applicable.
- Routing limitations:
  - ORS route dependence.
  - Static sea matrix and coastline factor.
  - No dynamic congestion, weather, or port queuing.
- Operational limitations:
  - No explicit schedule/service-frequency model.
  - No transit-time reliability model.
  - No explicit cargo volume constraints unless later implemented.
  - Simplified backhaul treatment.
- Maritime limitations:
  - Vessel class aggregation.
  - MRV transferability to Brazilian cabotage.
  - Hoteling assumptions.
- Cost limitations:
  - Fuel-centered or simplified cost structure, depending on final implementation.
  - Missing tariffs, insurance, inventory cost, port charges, or handling charges
    if not modeled.
- Data limitations:
  - Data vintage.
  - Missing ports or route pairs.
  - Calibration assumptions.

Robustness checkpoints:
- Every known simplification from the methodology chapter should appear here.
- Every major result-sensitive assumption should have either a sensitivity test or
  a stated future-work item.
- Do not hide limitations in footnotes.

Methodology debts to track:
- Finalize a debt table with columns: debt, current treatment, expected bias,
  severity, and future fix.
- Decide which debts are acceptable for an undergraduate thesis and which require
  pre-submission remediation.

Writing rules:
- Be explicit without apologizing for deliberate model scope.
- Distinguish "not modeled" from "modeled with simplified assumption."

### 10. Conclusion

Purpose:
Answer the research question and summarize the contribution.

Expected content:
- Direct answer to the core research question.
- Main corridor-level findings.
- Main methodological contribution.
- Practical implications.
- Highest-priority future improvements.

Robustness checkpoints:
- Conclusions must be supported by results already shown.
- No new data, methods, or findings should appear here.

Writing rules:
- Keep the conclusion concise.
- Use "within the modeled scope" for claims that depend on assumptions.

### References

Purpose:
Provide all academic, regulatory, API, and dataset citations.

Expected content:
- Freight/logistics literature.
- Emissions accounting references.
- ORS documentation.
- ANTAQ/ANTT/ANP/IBGE datasets and documents.
- EU MRV publication references.
- EMEP/EEA guidebook references.
- Any cost, fuel, or conversion-factor sources.

Robustness checkpoints:
- Every non-original number in the methodology must have a citation or data
  reference.
- Dataset access dates should be recorded where applicable.

Writing rules:
- Use one citation style consistently.
- Prefer primary sources over secondary summaries.

### Appendices

Purpose:
Keep the main text readable while preserving reproducibility detail.

Expected content:
- Appendix A: data inventory.
- Appendix B: formula reference and units.
- Appendix C: scenario configuration table.
- Appendix D: database/schema or persistence reference.
- Appendix E: reproducibility commands.
- Appendix F: additional sensitivity tables.
- Appendix G: selected logs or diagnostics, if useful.

Robustness checkpoints:
- Appendices should support auditability, not become a dumping ground.
- Any appendix table used to justify a result must be referenced in the main text.

Writing rules:
- Use stable labels for appendix tables and figures.
- Keep raw logs summarized unless exact excerpts are necessary.

## Cross-Chapter Methodology Robustness Checklist

- The same baseline scenario is used in methodology, experimental design, and
  results.
- All distances are labeled as road km, sea km, nautical miles, or converted km.
- All fuel quantities state unit and fuel type.
- All emissions state whether they are CO2 or CO2e and whether the boundary is
  TTW/TTT, TTW/TTW-like, WTW, or WTW-like.
- All costs state currency, price vintage, and included components.
- Every result table can be traced to one run, one input set, and one code version.
- Route cache behavior is documented so repeated runs are explainable.
- Missing data behavior is documented before final results.
- Sensitivity analyses vary one assumption family at a time unless explicitly
  labeled as combined scenarios.
- The final text does not imply precision beyond the quality of input data.

## Cross-Chapter Methodology Debt Register

| Debt | Current planning treatment | Required before final submission |
| --- | --- | --- |
| Persistence description drift | README and repo instructions may describe different durable backends over time. | Verify final implementation and document only the active persistence path. |
| Emissions scope | Planned as explicit TTW/TTW-like scope unless implementation changes. | Audit formulas and factors against final code. |
| CO2 vs CO2e | Planned as a named limitation if non-CO2 gases are excluded. | Confirm final emissions factors and labels. |
| Terminal operations | Planned as hoteling-only, embedded, or out-of-scope depending on final code. | State final treatment in Methodology and Limitations. |
| MRV transferability | MRV-derived vessel data may not perfectly represent Brazilian cabotage. | Discuss expected bias and add sensitivity where feasible. |
| Sea route realism | Static sea matrix/coastline factor simplifies actual sailing routes. | Document source, fallback, and sensitivity or limitation. |
| Cost completeness | Fuel-centered model may omit market tariffs and handling charges. | List included and excluded cost components. |
| Service frequency and transit time | Not part of first-order emissions/cost model unless added later. | Keep outside conclusions unless modeled. |
| Cargo constraints | Mass-based modeling may omit volume/cargo-mix constraints. | State scope and avoid TEU-specific claims unless supported. |
| Scenario freeze | Results need a reproducible run record. | Save final run metadata, input versions, and commands. |

## Writing Rules for the Whole TF

- Prefer precise, modest claims over broad sustainability claims.
- Use "origin-destination" or "O-D" consistently.
- Use "destination" in English prose; use repository variable names such as
  `destiny` only when referring to code or schemas that use that spelling.
- Define road-only and multimodal exactly once, then reuse those terms.
- State units in every table header.
- Do not mix kilometers and nautical miles without explicit conversion.
- Use "emissions" for mass of GHG/CO2 and "emissions intensity" for normalized
  indicators.
- Use "cost" only for components actually modeled.
- Keep assumptions near the formulas that use them.
- Keep limitations close to the claims they constrain.
- Avoid screenshots of code; use formulas, tables, and short path references.
- Keep implementation details subordinate to research logic.
- Do not include secrets, local machine paths, or private credentials.
- Preserve reproducibility: every reported figure should be traceable to code,
  input data, parameters, and run metadata.
