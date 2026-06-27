# TF Final Result Synthesis

## 1. Purpose and source scope

This synthesis consolidates the current thesis validation and sensitivity evidence into final result tables and defensible claim categories. It is intended as the direct basis for the Results and Discussion sections of the TF report.

Sources consolidated here:

- historical Batch 001 outputs from `docs/validation/tf_validation_batch_001_results.md`;
- Batch 001B planned, record-only, and methodology-decision rows from `docs/validation/tf_validation_batch_001b_results.md`, `docs/validation/tf_validation_batch_001b_methodology_decisions.md`, `docs/validation/tf_validation_batch_001b_output.csv`, and `docs/validation/tf_validation_batch_001b_output.json`;
- executed Batch 001B sensitivity rows from `docs/validation/tf_sensitivity_results_batch_001b.md`, `docs/validation/tf_validation_batch_001b_sensitivity_output.csv`, and `docs/validation/tf_validation_batch_001b_sensitivity_output.json`;
- blocked and excluded case decisions from the Batch 001B methodology and sensitivity documents.

No new model execution, sensitivity run, external source, maritime distance, port choice, service evidence, formula, factor, route optimization logic, or validation result is introduced here. Historical Batch 001 outputs remain diagnostic records and are not overwritten.

Issue #16 concluded that the executed sensitivity rows are `sensitive`, not `robust`. None of the executed sensitivity rows should be used as headline baseline conclusions by itself.

## 2. Final case inventory table

Cost output is shown as road-only / multimodal in BRL per shipment when available. Emissions output is shown as road-only / multimodal in kg TTW CO2e per shipment when available. `not executed` means the tracked artifact row does not contain numerical cost/emissions outputs.

| Case ID | Original case ID | OD pair | Cargo basis | Selected or forced ports | Case source | Road-only distance | Pre-carriage distance | Maritime distance | On-carriage distance | Maritime distance source | Maritime source type | Cost output | Emissions output | Validation or methodology status | Sensitivity classification | Final thesis use category |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001` | `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | 14 t / 1 TEU | Porto de Santos -> Porto de Santos | Batch 001 | 77.2 km | 86.174 km | 0.0 km | 9.031 km | SeaMatrix haversine fallback | `haversine_fallback` | BRL 315.87 / 419.23 | 138.3 / 183.6 kg CO2e | `reference_needed`; same-port issue later separated in Batch 001B | not assessed | `historical_diagnostic` |
| `TF-VAL-002` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | 14 t / 1 TEU | Porto de Santos -> Porto de Manaus | Batch 001 | 3870.0 km | 86.174 km | 2744.7 km | 6.763 km | SeaMatrix haversine fallback | `haversine_fallback` | BRL 16347.22 / 746.97 | 6937.5 / 583.8 kg CO2e | `reference_needed`; fallback maritime distance later tested | not assessed | `historical_diagnostic` |
| `TF-VAL-003` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | 14 t / 1 TEU | Porto de Manaus -> Porto de Fortaleza | Batch 001 | 5569.6 km | 7.563 km | 2391.2 km | 8.656 km | SeaMatrix haversine fallback | `haversine_fallback` | BRL 22986.28 / 378.91 | 9984.3 / 394.2 kg CO2e | `reference_needed`; exact Fortaleza evidence missing | not assessed | `historical_diagnostic` |
| `TF-VAL-004` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | 14 t / 1 TEU | Porto de Angra dos Reis -> Porto de Salvador | Batch 001 | 1472.9 km | 1369.936 km | 1273.3 km | 5.060 km | SeaMatrix haversine fallback | `haversine_fallback` | BRL 5935.87 / 5720.70 | 2640.4 / 2665.3 kg CO2e | `reference_needed`; Angra dos Reis later excluded for container benchmark | not assessed | `historical_diagnostic` |
| `TF-VAL-005` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | 14 t / 1 TEU | Porto do Rio Grande -> Porto do Recife | Batch 001 | 3768.6 km | 317.409 km | 3214.0 km | 1.850 km | SeaMatrix haversine fallback | `haversine_fallback` | BRL 15074.20 / 1685.21 | 6755.7 / 1058.6 kg CO2e | `reference_needed`; exact Recife evidence missing | not assessed | `historical_diagnostic` |
| `TF-VAL-001B-001` | `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | 14 t / 1 TEU | Porto de Santos -> Porto de Santos | Batch 001B planned | 77.2 km | 86.174 km | 0.0 km | 9.031 km | SeaMatrix haversine fallback | `haversine_fallback` | not executed | not executed | `warning_only`; `record_only_warning`; same-port/cabotage-inappropriate | not run | `limitation_example` |
| `TF-VAL-001B-002` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | 14 t / 1 TEU | Porto de Santos -> Porto de Manaus | Batch 001B planned | 3870.0 km | 86.174 km | 6111.6 km / 3300 nm | 6.763 km | Tracked external-reference summary | `external_reference` | not executed | not executed | artifact `blocked_methodology_decision`; methodology `sensitivity_only` | sensitivity setup | `sensitivity_discussion` |
| `TF-VAL-001B-003A` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | 14 t / 1 TEU | Porto de Manaus -> Porto de Fortaleza | Batch 001B planned | 5569.6 km | 7.563 km | 2391.2 km | 8.656 km | SeaMatrix haversine fallback | `haversine_fallback` | not executed | not executed | `blocked_reference_needed`; exact selected-port evidence missing | not run | `reference_needed` |
| `TF-VAL-001B-003B` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | 14 t / 1 TEU | Porto de Manaus -> forced BRPEC / Pecem | Batch 001B planned | 5569.6 km | 7.563 km | 2905.788 km / 1569 nm | 8.656 km | Tracked external-reference summary | `external_reference` | not executed | not executed | artifact `blocked_methodology_decision`; methodology `sensitivity_only` | sensitivity setup | `sensitivity_discussion` |
| `TF-VAL-001B-004A` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | 14 t / 1 TEU | Porto de Angra dos Reis -> Porto de Salvador | Batch 001B planned | 1472.9 km | 1369.936 km | 1273.3 km | 5.060 km | SeaMatrix haversine fallback | `haversine_fallback` | not executed | not executed | `excluded`; invalid Angra dos Reis container chain | not run | `excluded` |
| `TF-VAL-001B-004B` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | 14 t / 1 TEU | Original Angra dos Reis -> Salvador preserved; alternate origin port unresolved | Batch 001B planned | 1472.9 km | 1369.936 km | 1273.3 km | 5.060 km | SeaMatrix haversine fallback preserved from original chain | `haversine_fallback` | not executed | not executed | `blocked_missing_port`; methodology `planned_blocked_methodology_decision` | not run | `methodology_blocked` |
| `TF-VAL-001B-005A` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | 14 t / 1 TEU | Porto do Rio Grande -> Porto do Recife | Batch 001B planned | 3768.6 km | 317.409 km | 3214.0 km | 1.850 km | SeaMatrix haversine fallback | `haversine_fallback` | not executed | not executed | `blocked_reference_needed`; exact selected-port evidence missing | not run | `reference_needed` |
| `TF-VAL-001B-005B` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | 14 t / 1 TEU | Porto do Rio Grande -> forced BRSUA / Suape | Batch 001B planned | 3768.6 km | 317.409 km | 3415.088 km / 1844 nm | 1.850 km | Tracked external-reference summary | `external_reference` | not executed | not executed | artifact `blocked_methodology_decision`; methodology `sensitivity_only` | sensitivity setup | `sensitivity_discussion` |
| `TF-VAL-001B-SENS-002-REFDIST` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | 14 t / 1 TEU | forced Porto de Santos -> forced Porto de Manaus | Batch 001B sensitivity | 3883.5186 km | 84.6089 km | 6111.6 km / 3300 nm | 22.2574 km | Tracked external-reference summary | `external_reference` | BRL 18456.45 / 1263.50 | 6961.76 / 1104.67 kg CO2e | `sensitivity_executed`; reference-distance sensitivity only | `sensitive` | `sensitivity_discussion` |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | 14 t / 1 TEU | forced Porto de Manaus -> forced Porto do Pecem | Batch 001B sensitivity | 5572.6823 km | 22.1948 km | 2905.788 km / 1569 nm | 51.7574 km | Tracked external-reference summary | `external_reference` | BRL 26391.03 / 727.33 | 9989.83 / 573.48 kg CO2e | `sensitivity_executed`; Pecem alternate-port only | `sensitive` | `sensitivity_discussion` |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | 14 t / 1 TEU | forced Porto do Rio Grande -> forced Porto de Suape | Batch 001B sensitivity | 3912.2556 km | 325.1134 km | 3415.088 km / 1844 nm | 49.1101 km | Tracked external-reference summary | `external_reference` | BRL 18121.99 / 2122.38 | 7013.27 / 1127.46 kg CO2e | `sensitivity_executed`; Suape alternate-port only | `sensitive` | `sensitivity_discussion` |

## 3. Final thesis use categories

| Category | Meaning in this synthesis | Cases assigned |
| --- | --- | --- |
| `headline_candidate` | Candidate for headline Results claims after validation and sensitivity checks. | None. |
| `sensitivity_discussion` | Executed or planned sensitivity-only evidence that can be discussed with boundary warnings. | `TF-VAL-001B-002`; `TF-VAL-001B-003B`; `TF-VAL-001B-005B`; `TF-VAL-001B-SENS-002-REFDIST`; `TF-VAL-001B-SENS-003B-ALTPECEM`; `TF-VAL-001B-SENS-005B-ALTSUAPE`. |
| `limitation_example` | Useful to explain route-quality or method limitations, not numerical modal advantage. | `TF-VAL-001B-001`. |
| `excluded` | Invalid or out-of-scope for thesis numerical conclusions. | `TF-VAL-001B-004A`. |
| `reference_needed` | Exact selected-port reference evidence remains missing. | `TF-VAL-001B-003A`; `TF-VAL-001B-005A`. |
| `methodology_blocked` | A methodological decision or port selection is missing before execution. | `TF-VAL-001B-004B`. |
| `historical_diagnostic` | Original Batch 001 execution record preserved for traceability and comparison only. | `TF-VAL-001`; `TF-VAL-002`; `TF-VAL-003`; `TF-VAL-004`; `TF-VAL-005`. |

No current case qualifies as `headline_candidate`.

## 4. Sensitivity synthesis table

| Case ID | Scenario role | OD pair | Selected or forced ports | Varied parameter | Baseline assumption | Sensitivity assumption | Cost direction or result | Emissions direction or result | Classification | Safe thesis wording |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Santos/Manaus reference-distance sensitivity | Sao Paulo, SP -> Manaus, AM | forced Porto de Santos -> forced Porto de Manaus | Maritime distance | Original Batch 001 fallback `2744.7 km` from SeaMatrix haversine fallback. | `3300 nm` / `6111.6 km` external-reference candidate. | Multimodal remains lower in the tracked sensitivity output: BRL 18456.45 road-only vs BRL 1263.50 multimodal. | Multimodal remains lower in the tracked sensitivity output: 6961.76 kg TTW CO2e road-only vs 1104.67 kg TTW CO2e multimodal. | `sensitive` | Santos/Manaus can be discussed as a reference-distance sensitivity result, not a validated baseline replacement. |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Pecem alternate-port sensitivity | Manaus, AM -> Fortaleza, CE | forced Porto de Manaus -> forced Porto do Pecem | Destination port and maritime distance | Original selected-port row used Porto de Fortaleza and fallback `2391.2 km`. | Forced Pecem with `1569 nm` / `2905.788 km`. | Multimodal remains lower in the tracked alternate-port output: BRL 26391.03 road-only vs BRL 727.33 multimodal. | Multimodal remains lower in the tracked alternate-port output: 9989.83 kg TTW CO2e road-only vs 573.48 kg TTW CO2e multimodal. | `sensitive` | Pecem can be discussed only as an alternate-port sensitivity; it is not Porto de Fortaleza validation. |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Suape alternate-port sensitivity | Porto Alegre, RS -> Recife, PE | forced Porto do Rio Grande -> forced Porto de Suape | Destination port and maritime distance | Original selected-port row used Porto do Recife and fallback `3214.0 km`. | Forced Suape with `1844 nm` / `3415.088 km`. | Multimodal remains lower in the tracked alternate-port output: BRL 18121.99 road-only vs BRL 2122.38 multimodal. | Multimodal remains lower in the tracked alternate-port output: 7013.27 kg TTW CO2e road-only vs 1127.46 kg TTW CO2e multimodal. | `sensitive` | Suape can be discussed only as an alternate-port sensitivity; it is not Porto do Recife validation. |

All three executed sensitivity rows are `sensitive`, not `robust`.

## 5. Excluded and blocked cases table

| Case ID | Reason for exclusion or blocker | Needed before future use | Safe thesis use |
| --- | --- | --- | --- |
| `TF-VAL-001B-001` | Same-port Santos -> Santos row is cabotage-inappropriate for a normal road-sea-road corridor. | A separate model-boundary decision for local same-port route behavior. | limitation |
| `TF-VAL-001B-003A` | Exact Porto de Manaus -> Porto de Fortaleza maritime distance/source is missing. Pecem cannot be substituted. | Exact selected-port distance/source with unit and provenance. | reference gap |
| `TF-VAL-001B-004A` | Angra dos Reis selected-origin chain is invalid/excluded for the current 1 TEU / 14 t container benchmark. | A defensible different origin-port methodology or changed cargo boundary. | excluded |
| `TF-VAL-001B-004B` | No defensible Brasilia -> Salvador alternate origin port or maritime distance/source is documented. | Select and document a defensible alternate origin port and distance source. | future work |
| `TF-VAL-001B-005A` | Exact Porto do Rio Grande -> Porto do Recife maritime distance/source is missing. Suape cannot be substituted. | Exact selected-port distance/source with unit and provenance. | reference gap |

These cases must not be used for numerical headline conclusions.

## 6. Allowed thesis claims

Safe claims:

- CabotageLens provides a reproducible, route-aware comparison framework for road-only and road-cabotage-road alternatives.
- Results are corridor-specific and boundary-specific.
- The current environmental boundary is operational TTW CO2e, not WTW or LCA.
- The current cost outputs are model cost estimates, not full commercial freight rates.
- Executed Batch 001B sensitivity rows show that, under the current operational TTW CO2e and model-cost boundary, the modeled multimodal option remains lower than road-only in the three named sensitivity scenarios.
- The magnitude of the modeled advantage is sensitive to maritime distance, port choice, and boundary assumptions.
- Batch 001B improves auditability by preserving maritime-distance provenance, source type, original values, forced-port information, and validation or methodology status.
- Exact Fortaleza and Recife selected-port claims remain unresolved until exact selected-port distance evidence is documented.

## 7. Prohibited thesis claims

Do not claim:

- cabotage is universally better;
- model cost equals a commercial freight rate;
- sensitivity rows validate exact selected-port baselines;
- Pecem equals Porto de Fortaleza;
- Suape equals Porto do Recife;
- TTW results represent WTW or LCA;
- invalid or blocked cases support headline conclusions;
- fallback maritime distance alone validates a route;
- cost and emissions can be collapsed into a single winner without an explicit decision rule;
- historical Batch 001 fallback outputs are corrected results;
- alternate-port sensitivity rows are silent replacements for model-selected ports.

## 8. Recommended wording for final TF

Results:

> The Batch 001 validation runs are retained as historical diagnostic outputs. The corrected Batch 001B layer separates record-only, blocked, excluded, and sensitivity-only cases. No current case is classified as a headline baseline result. In the three executed Batch 001B sensitivity scenarios, the modeled multimodal option remains lower than road-only for model cost estimate and operational TTW CO2e, but those rows are classified as sensitive rather than robust.

Discussion:

> The sensitivity results show that documented maritime-distance and alternate-port assumptions can materially affect the magnitude and interpretation of the road-cabotage-road comparison. Santos/Manaus is a reference-distance sensitivity, while Pecem and Suape are alternate-port sensitivities. These scenarios support discussion of model behavior under documented assumptions, not validation of exact selected-port baselines.

Limitations:

> Several cases remain unsuitable for numerical conclusions. Same-port Santos/Santos is a route-logic limitation, Manaus/Fortaleza and Rio Grande/Recife still lack exact selected-port maritime references, the Angra dos Reis chain is excluded for the container benchmark, and Brasilia/Salvador lacks a defensible alternate origin-port decision. Cost outputs remain model estimates rather than commercial freight rates, and emissions remain operational TTW CO2e rather than WTW or LCA.

Conclusion:

> The thesis can conclude that CabotageLens produces auditable, boundary-explicit comparisons and that Batch 001B improves traceability for maritime distance, port selection, and sensitivity interpretation. It should not conclude that cabotage is universally better or that the sensitivity rows are validated baseline results. Future work should close selected-port reference gaps, expand source-supported sensitivity ranges, and test broader cost-boundary assumptions before headline corridor claims are made.
