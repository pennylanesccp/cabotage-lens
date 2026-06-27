# Batch 001B Methodology Decisions

## 1. Purpose And Source Scope

This document finalizes the Batch 001B methodology-decision layer before issue #16 sensitivity work. It decides which tracked Batch 001B cases are executable, sensitivity-only, blocked, record-only, or excluded.

This document uses only tracked repository evidence:

- `docs/validation/tf_validation_batch_001b_rerun_assumptions.md`
- `docs/validation/tf_validation_batch_001b_config.json`
- `docs/validation/tf_validation_batch_001b_output.csv`
- `docs/validation/tf_validation_batch_001b_output.json`
- `docs/validation/tf_validation_batch_001b_results.md`
- `docs/validation/tf_validation_batch_001_external_references.md`
- `docs/validation/tf_validation_batch_001_results.md`
- `docs/tf_literature_audit_implementation_plan.md`
- `docs/tf_system_boundary.md`
- `docs/port_ops_model.md`
- implemented provenance and route-warning hooks in `modules/validation/batch_001b.py`, `modules/multimodal/distance_provenance.py`, and `modules/multimodal/route_quality.py`

No new external sources, sensitivity runs, broad model reruns, formula changes, or numerical factor changes are introduced here. The original Batch 001 execution record remains historical evidence and must not be overwritten by Batch 001B decisions.

## 2. Maritime-Distance Decision Rules

| Decision point | Rule | Methodology consequence |
| --- | --- | --- |
| SeaMatrix distance as baseline | A SeaMatrix value can be treated as the baseline only when it is available for the exact selected or explicitly forced port pair, has provenance or source typing as `seamatrix`, has explicit units, is not a same-port or zero-sea edge case, and does not rely on fallback logic. | The case may move toward `execute_ready` only after all other execution gates are also satisfied. A SeaMatrix baseline is still a modeled distance, not proof of service frequency, freight rates, or terminal productivity. |
| `haversine_fallback` distance | A `haversine_fallback` maritime distance is only a screening estimate. It can preserve the original Batch 001 record and can explain why a case needs correction or sensitivity, but it must not be used for strong thesis conclusions by itself. | Cases depending only on fallback distance remain `reference_needed`, `record_only_warning`, `excluded`, or sensitivity setup. They cannot support headline cost or TTW CO2e conclusions without correction or sensitivity treatment. |
| Exact external reference | An external maritime-distance reference can become a corrected scenario only when it matches the exact selected or forced port pair, records unit and source/provenance, uses an explicit conversion rule, and the methodology decision states whether it is a replacement, bound, or named sensitivity scenario. | If the reference matches the selected/forced ports and all gates are satisfied, the case can become `execute_ready`. If the decision is to test the reference rather than replace the baseline, the case remains `sensitivity_only`. |
| Nearby-port external reference | A reference for a nearby but different port cannot validate the original selected-port case. Pecem is not Porto de Fortaleza. Suape is not Porto do Recife. | The case can only be an explicitly labeled alternate-port sensitivity, with forced-port provenance and road-access treatment visible. It must not be reported as original selected-port validation. |
| Missing exact reference | If exact selected-port maritime distance evidence is missing and no accepted forced-port sensitivity rule exists, the case remains blocked. | The readiness class is `reference_needed` unless the missing item is a methodology choice rather than a source gap. No invented distance, inferred substitute, or silent conversion is allowed. |
| Same-port case | Same selected origin and destination ports are treated as a warning/exclusion case, not a meaningful cabotage corridor. | The case is `record_only_warning` or `excluded`. It should support route-logic limitations, not numerical road-sea-road performance conclusions. |
| Original Batch 001 preservation | Original Batch 001 values must remain visible beside Batch 001B values through original distance/source fields and historical documentation. | Batch 001B can add corrected or sensitivity rows, but it must not rewrite or replace the historical Batch 001 output. |

The nautical-mile conversion rule already used by the Batch 001B pathway is `1 nm = 1.852 km`. Any case using a nautical-mile external reference must preserve both the source unit and the converted kilometre value.

## 3. Readiness Classes

| Readiness class | Meaning | Use in issue #16 | Headline thesis conclusions | Appendix, limitation, or sensitivity use |
| --- | --- | --- | --- | --- |
| `execute_ready` | All execution gates are satisfied for an original selected-port case or an explicitly forced corrected case. Maritime source, unit, ports, boundary, and original-value preservation are complete. | Yes, if issue #16 needs an executed corrected scenario. | Only after execution and boundary review; not from readiness alone. | Yes, with provenance and boundary notes. |
| `sensitivity_only` | The case has a documented assumption suitable for sensitivity, but it is not a validated baseline. This includes reference-distance tests and alternate-port scenarios. | Yes, as named sensitivity analysis only. | No. It cannot support headline claims as the original corridor. | Yes. It belongs in sensitivity results, appendix tables, and limitations. |
| `planned_blocked_methodology_decision` | A source or artifact exists only as a plan, but a methodology choice is still missing, such as selecting a defensible alternate origin port or deciding the treatment of a candidate. | Not now. It can enter issue #16 only after the decision and evidence are recorded. | No. | Yes, as a blocker or future-work item. |
| `reference_needed` | The exact selected-port distance/source remains missing from tracked evidence. | No, unless a future task adds the missing reference and updates the decision. | No. | Yes, as a reference gap and limitation. |
| `record_only_warning` | The row is retained to document warning logic, same-port behavior, or a non-executable edge case. | No numerical sensitivity execution. | No, except as a limitation about route-selection behavior. | Yes, as a limitation or audit-trail row. |
| `excluded` | The case is not valid for the current 1 TEU / 14 t container benchmark or current route boundary. | No. | No, except as evidence for excluding an invalid chain. | Yes, as an exclusion rationale or limitation example. |

No tracked Batch 001B case is currently classified as `execute_ready` for headline thesis conclusions.

## 4. Case Classification

| Case ID | Original case ID | OD pair | Selected or forced ports | Maritime distance source/provenance status | Current blocker | Readiness class | Recommended next action | Eligible for issue #16 sensitivity analysis? | Can support final thesis headline conclusions? | Safe thesis wording |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | `Porto de Santos` -> `Porto de Santos`; no forced ports | Same-port `0.0 km` sea leg. Original source preserved as `SeaMatrix haversine fallback`; normalized source type is `haversine_fallback`. | Same origin and destination port; cabotage-inappropriate local edge case. | `record_only_warning` | Keep as a warning/exclusion record. Do not run as a normal cabotage scenario. | No. | No; limitation only. | This local same-port case is a route-selection limitation, not evidence of cabotage performance. |
| `TF-VAL-001B-002` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | `Porto de Santos` -> `Porto de Manaus`; no forced ports | Documented external reference candidate `3300 nm` / `6111.6 km` for Santos/Manaus is preserved. Original fallback `2744.7 km` is preserved beside it. | The reference should be used as a named sensitivity distance, not as a validated baseline replacement. | `sensitivity_only` | Use as `TF-VAL-001B-SENS-002-REFDIST` or equivalent named reference-distance sensitivity. Preserve the original fallback comparison. | Yes, as sensitivity only. | No. | Santos/Manaus sensitivity can show how route-distance assumptions affect estimates; it does not by itself validate final cost or TTW CO2e advantage. |
| `TF-VAL-001B-003A` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | `Porto de Manaus` -> `Porto de Fortaleza`; no forced ports | Exact selected-port reference is missing. Original fallback `2391.2 km` is preserved as historical output only. | Exact Porto de Manaus -> Porto de Fortaleza maritime distance/source is not documented; Pecem must not be substituted. | `reference_needed` | Keep blocked until exact selected-port distance/source evidence is added, or keep as a documented reference gap. | No. | No. | The original Manaus/Fortaleza selected-port maritime distance remains unresolved. |
| `TF-VAL-001B-003B` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | Original selected ports were `Porto de Manaus` -> `Porto de Fortaleza`; forced alternate destination is `BRPEC` / Pecem. | Documented external alternate-port reference `1569 nm` / `2905.788 km` for Manaus/Pecem is preserved. Original Fortaleza fallback `2391.2 km` is preserved beside it. | This is a nearby-port scenario. It cannot validate Porto de Fortaleza and must keep Pecem road-access and boundary implications visible. | `sensitivity_only` | Use only as a named Pecem alternate-port sensitivity. Do not report it as Fortaleza validation. | Yes, as alternate-port sensitivity only. | No. | Pecem can be discussed as a Fortaleza-region alternate-port sensitivity, not as Porto de Fortaleza validation. |
| `TF-VAL-001B-004A` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | `Porto de Angra dos Reis` -> `Porto de Salvador`; no forced ports | Original fallback `1273.3 km` is preserved as historical output only. | Angra dos Reis is not defensible for the current 1 TEU / 14 t container benchmark. | `excluded` | Keep as excluded. Do not rerun as a corrected or sensitivity case under the current selected-port chain. | No. | No; exclusion rationale only. | The Angra dos Reis chain is an operational-plausibility failure under the container benchmark. |
| `TF-VAL-001B-004B` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | Original selected ports were `Porto de Angra dos Reis` -> `Porto de Salvador`; no defensible forced alternate origin port is selected. | No alternate-origin maritime distance/source is documented. Current planned row only preserves the original fallback chain. | Missing methodology decision and evidence for the alternate origin port and its maritime distance rule. | `planned_blocked_methodology_decision` | Select and document a defensible alternate origin port and source/provenance before issue #16 can use it. | Not now; only after the port and distance decision. | No. | No quantitative Brasilia/Salvador corrected-chain claim is defensible until the alternate origin port and distance source are documented. |
| `TF-VAL-001B-005A` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | `Porto do Rio Grande` -> `Porto do Recife`; no forced ports | Exact selected-port reference is missing. Original fallback `3214.0 km` is preserved as historical output only. | Exact Porto do Rio Grande -> Porto do Recife maritime distance/source is not documented; Suape must not be substituted. | `reference_needed` | Keep blocked until exact selected-port distance/source evidence is added, or keep as a documented reference gap. | No. | No. | The Rio Grande/Recife selected-port maritime distance remains unresolved; Suape evidence cannot validate Recife. |
| `TF-VAL-001B-005B` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | Original selected ports were `Porto do Rio Grande` -> `Porto do Recife`; forced alternate destination is `BRSUA` / Suape. | Documented external alternate-port reference `1844 nm` / `3415.088 km` for Rio Grande/Suape is preserved. Original Recife fallback `3214.0 km` is preserved beside it. | This is a nearby-port scenario. It cannot validate Porto do Recife and must keep Suape road-access and boundary implications visible. | `sensitivity_only` | Use only as a named Suape alternate-port sensitivity. Do not report it as Recife validation. | Yes, as alternate-port sensitivity only. | No. | Suape can be discussed as a Pernambuco alternate-port sensitivity, not as Porto do Recife validation. |

## 5. Execution Readiness Gates

Before any Batch 001B case can be run with `--execute`, every applicable gate below must be satisfied:

- Maritime distance source and provenance are available.
- Unit and conversion rule are explicit, including `1 nm = 1.852 km` when nautical miles are used.
- Selected or forced ports are explicit.
- Any forced-port or alternate-port scenario is labeled as such and is not presented as original selected-port validation.
- Fallback maritime distances are not used for strong thesis conclusions without correction or sensitivity treatment.
- TTW CO2e and cost-estimate boundaries are preserved in outputs and interpretation.
- Original Batch 001 output is preserved for comparison through original-value fields and historical documentation.
- No invented values, inferred distances, undocumented port choices, or untracked sources are introduced.
- There is no silent substitution of Pecem for Fortaleza or Suape for Recife.
- Same-port or cabotage-inappropriate cases remain warning/exclusion records unless a future issue explicitly changes the model boundary.

Passing these gates makes a row executable for its declared purpose. It does not automatically make the result thesis-validated, commercially validated, or suitable for headline conclusions.

## Handoff to issue #16

Cases eligible for sensitivity analysis now:

| Case | Issue #16 role | Exact reason |
| --- | --- | --- |
| `TF-VAL-001B-002` | Reference-distance sensitivity | Santos/Manaus has a documented `3300 nm` external reference candidate for the selected port pair, with original fallback preserved. Use it as sensitivity, not a validated baseline replacement. |
| `TF-VAL-001B-003B` | Alternate-port sensitivity | Manaus/Pecem has a documented `1569 nm` external reference candidate, but Pecem is not Porto de Fortaleza. Use only as a labeled alternate-port scenario. |
| `TF-VAL-001B-005B` | Alternate-port sensitivity | Rio Grande/Suape has a documented `1844 nm` external reference candidate, but Suape is not Porto do Recife. Use only as a labeled alternate-port scenario. |

Cases eligible only after a methodology decision:

| Case | Blocker | Required decision before issue #16 |
| --- | --- | --- |
| `TF-VAL-001B-004B` | No defensible alternate origin port and no alternate-origin maritime distance/source are documented. | Select a container/cabotage-defensible alternate origin port for Brasilia -> Salvador, document port provenance, and record a maritime distance source and unit. |

Cases excluded from issue #16 numerical execution:

| Case | Exact reason for exclusion |
| --- | --- |
| `TF-VAL-001B-001` | Same-port Santos -> Santos row is a warning/exclusion record, not a meaningful cabotage corridor or sensitivity case. |
| `TF-VAL-001B-004A` | Original Angra dos Reis -> Salvador chain is invalid/excluded for the current 1 TEU / 14 t container benchmark. |
| `TF-VAL-001B-003A` | Exact Manaus -> Porto de Fortaleza maritime distance/source remains missing; Pecem cannot be substituted into this selected-port row. |
| `TF-VAL-001B-005A` | Exact Rio Grande -> Porto do Recife maritime distance/source remains missing; Suape cannot be substituted into this selected-port row. |

Cases that should remain record-only or limitation examples:

| Case | Limitation use |
| --- | --- |
| `TF-VAL-001B-001` | Use as a same-port route-quality warning and cabotage-inappropriate edge case. |
| `TF-VAL-001B-004A` | Use as an operational-plausibility failure for the selected Angra dos Reis container chain. |
| `TF-VAL-001B-003A` | Use as evidence that exact selected-port maritime references are still missing for Fortaleza. |
| `TF-VAL-001B-005A` | Use as evidence that exact selected-port maritime references are still missing for Recife. |

Issue #16 should therefore execute, if requested, only the named sensitivity rows derived from `TF-VAL-001B-002`, `TF-VAL-001B-003B`, and `TF-VAL-001B-005B`. It should not execute `TF-VAL-001B-001`, `TF-VAL-001B-003A`, `TF-VAL-001B-004A`, `TF-VAL-001B-004B`, or `TF-VAL-001B-005A` unless a later methodology or reference task resolves the stated blockers.
