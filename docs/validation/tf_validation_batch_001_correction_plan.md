# Batch 001 Correction Plan

## 1. Purpose

This document defines what must be corrected, bounded, excluded, or rerun before Batch 001 validation cases can support thesis conclusions. It converts the status update in `docs/validation/tf_validation_batch_001_status_update.md` into concrete next actions for route logic, alternate-port assumptions, maritime-distance replacement or bounding, and rerun readiness.

This is a methodological planning document, not a model execution result. It does not change the raw Batch 001 outputs recorded in `docs/validation/tf_validation_batch_001_results.md`, does not introduce new model outputs, and does not mark any case as fully validated.

## 2. Batch-level correction principles

- Do not use `SeaMatrix haversine fallback` as the sole basis for strong maritime-distance, emissions, cost, or road-sea-road advantage conclusions.
- Do not silently substitute nearby ports, such as Pecem for Fortaleza or Suape for Recife.
- Do not use ports without container/cabotage relevance for a 1 TEU / 14 t benchmark case.
- Treat same-port selections as cabotage-inappropriate movements or route-logic edge cases, not as normal cabotage corridors.
- If the operationally relevant port differs from the model-selected port, create an explicit alternate-port scenario.
- Preserve the original Batch 001 results as the raw execution record for comparison.
- Rerun only after assumptions are explicit enough to defend academically.
- Keep cost and emissions interpretation conditional until route, distance, service, and boundary assumptions are aligned.

## 3. Case-by-case correction plan

### `TF-VAL-001`: Sao Paulo (SP) -> Santos (SP)

Current recommended status from `tf_validation_batch_001_status_update.md`: `pass_with_limitation`.

Current model-selected ports: `Porto de Santos` -> `Porto de Santos`.

Core issue: The model selected the same port for origin and destination and recorded a `0.0 km sea` leg using `SeaMatrix haversine fallback`. This is a close-to-port route-logic edge case, not a meaningful cabotage corridor.

Correction decision:

- Keep the case as a same-port / close-to-port edge case.
- Do not rerun this as a normal cabotage route.
- Add a methodological rule that if origin and destination resolve to the same port, the case should be labeled cabotage-inappropriate or excluded from road-sea-road advantage conclusions.

Required evidence before rerun:

- No normal rerun evidence is required.
- If the case remains in a quantitative appendix, keep or add a road-distance interpretation note for the local Sao Paulo -> Santos movement.
- If future code implements a same-port warning or exclusion, verify that the warning preserves the original Batch 001 result for comparison.

Rerun needed: no, unless future code implements a same-port warning or exclusion behavior that needs to be checked.

Proposed corrected or alternate scenario: `Sao Paulo (SP) -> Santos (SP)` retained as a same-port exclusion/warning case, with `Porto de Santos` -> `Porto de Santos` treated as cabotage-inappropriate.

Can the original Batch 001 output support thesis conclusions? It can support a route-logic limitation only. It should not support a conclusion that cabotage is operationally advantageous or disadvantageous for this OD pair.

Recommended thesis treatment: Use as a methodological edge case showing why same-port cabotage construction must be labeled, filtered, or excluded from road-sea-road advantage claims.

### `TF-VAL-002`: Sao Paulo (SP) -> Manaus (AM)

Current recommended status from `tf_validation_batch_001_status_update.md`: `sensitivity_required`.

Current model-selected ports: `Porto de Santos` -> `Porto de Manaus`.

Core issue: The selected port pair is operationally plausible, but the maritime distance used by the model came from `SeaMatrix haversine fallback`. The external references document identifies an ANTAQ-based nautical-mile reference for the Santos/Manaus corridor that must be used to replace or bound the fallback distance before strong conclusions are drawn.

Correction decision:

- Keep the port pair `Porto de Santos` -> `Porto de Manaus`.
- Replace or bound the maritime distance using the ANTAQ-based nautical-mile reference identified in `docs/validation/tf_validation_batch_001_external_references.md`.
- Prepare a rerun or sensitivity scenario comparing the original fallback-distance result against the corrected or bounded maritime-distance assumption.

Required evidence before rerun:

- A documented rule for how the ANTAQ-based nautical-mile reference is converted, bounded, or applied.
- A clear statement of whether the corrected distance is treated as a single replacement value or as a sensitivity bound.
- Service-plausibility note confirming that the Santos/Manaus corridor is relevant to the 1 TEU / 14 t benchmark.
- Confirmation that cost and emissions boundaries remain unchanged unless explicitly documented.

Rerun needed: yes, after the distance-bounding rule is defined.

Proposed corrected or alternate scenario: `Sao Paulo (SP) -> Manaus (AM)` with `Porto de Santos` -> `Porto de Manaus`, comparing the original fallback maritime distance with the corrected or bounded maritime distance.

Can the original Batch 001 output support thesis conclusions? Not as a validated quantitative result. It can support a sensitivity-motivation discussion and show that the corridor is plausible but distance-sensitive.

Recommended thesis treatment: Use only as a conditional case until the corrected or bounded maritime distance is rerun and compared against the original fallback result.

### `TF-VAL-003`: Manaus (AM) -> Fortaleza (CE)

Current recommended status from `tf_validation_batch_001_status_update.md`: `reference_needed`.

Current model-selected ports: `Porto de Manaus` -> `Porto de Fortaleza`.

Core issue: The model selected Fortaleza, while existing evidence also points to Pecem as an important nearby comparator. Pecem must not be substituted silently for Fortaleza, and regional service plausibility is not enough to validate the exact model-selected port pair.

Correction decision:

- Do not silently replace Fortaleza with Pecem.
- Create two possible paths:
  - keep `Porto de Fortaleza` only if exact service and distance evidence is found for the model-selected pair;
  - create an explicit alternate-port scenario using Pecem if evidence supports it.
- Document this as a port-boundary issue between the model-selected Fortaleza port and a potentially more operationally relevant Pecem port node.

Required evidence before rerun:

- Exact service and maritime-distance evidence for `Porto de Manaus` -> `Porto de Fortaleza`, or a documented reason to use a Pecem alternate scenario.
- If Pecem is used, an explicit statement that this is an alternate-port scenario, not a correction silently applied to the original result.
- Road access implications for the Fortaleza versus Pecem destination assumption.
- Confirmation that the cargo basis remains 1 TEU / 14 t.

Rerun needed: yes, if Pecem is selected as an alternate port or if corrected maritime distance is added for the Fortaleza case.

Proposed corrected or alternate scenario: Keep `Porto de Manaus` -> `Porto de Fortaleza` only with exact evidence, and separately define `Porto de Manaus` -> Pecem as an alternate-port scenario if supported.

Can the original Batch 001 output support thesis conclusions? No. It should not support thesis conclusions until the exact Fortaleza port pair is evidenced or an explicit Pecem alternate scenario is created.

Recommended thesis treatment: Present as an unresolved port-boundary case. Separate the model-selected Fortaleza output from any Pecem-based operational interpretation.

### `TF-VAL-004`: Brasilia (DF) -> Salvador (BA)

Current recommended status from `tf_validation_batch_001_status_update.md`: `fail_operational_plausibility`.

Current model-selected ports: `Porto de Angra dos Reis` -> `Porto de Salvador`.

Core issue: The model selected Angra dos Reis as the origin port, but the external references document records evidence that Angra dos Reis is not operationally defensible as a container/cabotage origin for the 1 TEU / 14 t benchmark case.

Correction decision:

- Do not use `Porto de Angra dos Reis` for the 1 TEU / 14 t container benchmark.
- Either exclude the original case from thesis-supporting conclusions or create an alternate-port scenario using a defensible container/cabotage origin port.
- Candidate alternate origin ports remain candidates only until supported by evidence and selected under an explicit rerun assumption.

Candidate alternate origin ports to investigate, not final decisions:

- Rio de Janeiro or Itaguai, if evidence supports container/cabotage relevance and a defensible access-leg boundary from Brasilia.
- Santos, if the thesis boundary justifies a longer access leg to a stronger container/cabotage node.
- Another container/cabotage origin port, only if supported by documented service and distance evidence.

Required evidence before rerun:

- Evidence that the selected alternate origin port is container/cabotage relevant for the benchmark cargo.
- A documented road access implication from Brasilia to the alternate origin port.
- A corrected or bounded maritime distance from the alternate origin port to `Porto de Salvador`.
- A clear exclusion note for the original Angra dos Reis result.

Rerun needed: yes, only if an alternate port is selected.

Proposed corrected or alternate scenario: Exclude or mark invalid the original `Porto de Angra dos Reis` -> `Porto de Salvador` road-sea-road chain; optionally create a new Brasilia -> Salvador alternate-origin-port scenario after evidence supports a specific port.

Can the original Batch 001 output support thesis conclusions? No. It should not support thesis conclusions in its current model-selected form.

Recommended thesis treatment: Treat as a route-logic and operational-plausibility failure for the selected port pair. Use it to justify alternate-port controls or exclusion rules, not as evidence of cabotage performance.

### `TF-VAL-005`: Porto Alegre (RS) -> Recife (PE)

Current recommended status from `tf_validation_batch_001_status_update.md`: `reference_needed`.

Current model-selected ports: `Porto do Rio Grande` -> `Porto do Recife`.

Core issue: The model selected Recife, while existing evidence is stronger for Suape as a Pernambuco container/cabotage comparator. Suape must not be substituted silently for Recife, and the model-selected destination remains unresolved.

Correction decision:

- Do not silently replace Recife with Suape.
- Create two possible paths:
  - keep `Porto do Recife` only if exact service and maritime-distance evidence is found;
  - create an explicit alternate-port scenario using Suape if evidence supports it.
- Document this as a Pernambuco port-boundary issue.

Required evidence before rerun:

- Exact service and maritime-distance evidence for `Porto do Rio Grande` -> `Porto do Recife`, or a documented reason to use Suape as an alternate scenario.
- If Suape is used, an explicit statement that this is an alternate-port scenario, not a correction silently applied to the original result.
- Road access implications for Recife versus Suape as the destination port.
- Confirmation that the cargo basis remains 1 TEU / 14 t.

Rerun needed: yes, if Suape is selected as alternate or if corrected maritime distance is added for the Recife case.

Proposed corrected or alternate scenario: Keep `Porto do Rio Grande` -> `Porto do Recife` only with exact evidence, and separately define `Porto do Rio Grande` -> Suape as an alternate-port scenario if supported.

Can the original Batch 001 output support thesis conclusions? No. It can motivate a port-boundary correction, but it should not support thesis conclusions until the Recife versus Suape assumption is explicit.

Recommended thesis treatment: Present as an unresolved Pernambuco destination-port case. Separate the model-selected Recife output from any Suape-based operational interpretation.

## 4. Rerun readiness checklist

A Batch 001 case is ready to rerun only when all applicable items below are complete:

- [ ] Corrected or bounded maritime distance selected.
- [ ] Model-selected or alternate port pair explicitly defined.
- [ ] Service plausibility documented for the chosen port pair.
- [ ] Road access implications documented for origin and destination access legs.
- [ ] Cargo basis confirmed as 1 TEU / 14 t.
- [ ] Cost and emissions boundaries unchanged or explicitly documented.
- [ ] Expected output fields listed before execution.
- [ ] Original Batch 001 result preserved for comparison.
- [ ] Any same-port, invalid-port, or alternate-port treatment explicitly labeled.
- [ ] No case is marked as fully validated before rerun evidence is reviewed.

## 5. Proposed Batch 001B rerun set

Future corrected or bounded cases should be tracked as `Batch 001B`. The table below is a proposed rerun set, not an execution record.

| New Case ID | Original Case | OD pair | Port assumption | Correction type | Rerun priority | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001` | Sao Paulo (SP) -> Santos (SP) | `Porto de Santos` -> `Porto de Santos`; same-port exclusion/warning only | Route-logic labeling | low | No normal rerun. Rerun only if future code implements same-port warning or exclusion behavior. |
| `TF-VAL-001B-002` | `TF-VAL-002` | Sao Paulo (SP) -> Manaus (AM) | `Porto de Santos` -> `Porto de Manaus` | Corrected or bounded maritime distance | high | Compare original fallback result against ANTAQ-based corrected or bounded maritime distance. |
| `TF-VAL-001B-003A` | `TF-VAL-003` | Manaus (AM) -> Fortaleza (CE) | `Porto de Manaus` -> `Porto de Fortaleza` | Exact selected-port evidence | high | Keep Fortaleza only if exact service and distance evidence is found. |
| `TF-VAL-001B-003B` | `TF-VAL-003` | Manaus (AM) -> Fortaleza/Pecem | `Porto de Manaus` -> Pecem, if selected explicitly | Alternate-port scenario | medium | Use only if Pecem is selected with explicit evidence and boundary notes. |
| `TF-VAL-001B-004A` | `TF-VAL-004` | Brasilia (DF) -> Salvador (BA) | `Porto de Angra dos Reis` -> `Porto de Salvador` | Exclusion or invalid selected-port marking | high | Do not treat as a normal cabotage rerun. Mark original selected-port chain invalid for the benchmark cargo. |
| `TF-VAL-001B-004B` | `TF-VAL-004` | Brasilia (DF) -> Salvador (BA) | Defensible alternate origin port -> `Porto de Salvador`, to be selected | Alternate-port scenario | high | Select the origin port only after evidence supports container/cabotage relevance and road access assumptions. |
| `TF-VAL-001B-005A` | `TF-VAL-005` | Porto Alegre (RS) -> Recife (PE) | `Porto do Rio Grande` -> `Porto do Recife` | Exact selected-port evidence | high | Keep Recife only if exact service and distance evidence is found. |
| `TF-VAL-001B-005B` | `TF-VAL-005` | Porto Alegre (RS) -> Suape | `Porto do Rio Grande` -> Suape, if selected explicitly | Alternate-port scenario | medium | Use only if Suape is selected with explicit evidence and Pernambuco boundary notes. |

## 6. Recommended next issue

Recommended next issue:

`Define Batch 001B rerun assumptions and required code/data hooks`

That issue should determine whether the current code can force or override selected ports and maritime distances for validation reruns, or whether a small rerun utility or configuration file is needed. It should remain methodology-first and should define the required hooks before any model execution.

The next issue should identify:

- how to specify same-port exclusion or warning behavior for `TF-VAL-001B-001`;
- how to provide corrected or bounded maritime distances for `TF-VAL-001B-002`;
- whether Fortaleza, Pecem, Recife, Suape, and alternate Brasilia-origin ports can be forced explicitly in reruns;
- how to preserve original Batch 001 outputs beside Batch 001B outputs;
- which fields must be exported after rerun for thesis comparison;
- how to document any unchanged cost and emissions boundaries.
