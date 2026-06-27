# TF Sensitivity Results - Batch 001B

## 1. Purpose

This document is the thesis-ready issue #16 sensitivity result artifact for Batch 001B. It consolidates the tracked Batch 001B sensitivity execution and interprets it under the methodology-decision handoff in:

- `docs/validation/tf_validation_batch_001b_methodology_decisions.md`
- `docs/validation/tf_validation_batch_001b_results.md`
- `docs/validation/tf_validation_batch_001b_rerun_assumptions.md`
- `docs/validation/tf_validation_batch_001b_sensitivity_decisions.md`
- `docs/validation/tf_validation_batch_001b_sensitivity_results.md`
- `docs/validation/tf_validation_batch_001b_sensitivity_output.csv`
- `docs/validation/tf_validation_batch_001b_sensitivity_output.json`

No new model execution, sensitivity run, web research, external source, emission factor, fuel consumption formula, cost formula, routing rule, port choice, or maritime distance is introduced in this document. The numerical results below come from the tracked Batch 001B sensitivity output artifacts.

Issue #16 uses only these named sensitivity cases:

- `TF-VAL-001B-002` as Santos/Manaus reference-distance sensitivity through `TF-VAL-001B-SENS-002-REFDIST`.
- `TF-VAL-001B-003B` as Pecem alternate-port sensitivity through `TF-VAL-001B-SENS-003B-ALTPECEM`.
- `TF-VAL-001B-005B` as Suape alternate-port sensitivity through `TF-VAL-001B-SENS-005B-ALTSUAPE`.

No eligible case becomes a validated baseline, exact selected-port validation, or headline thesis conclusion merely because it appears in this sensitivity analysis.

## 2. Existing Sensitivity Support Audited

The repository already contains a focused Batch 001B sensitivity path:

| Artifact or code path | Role in this issue |
| --- | --- |
| `scripts/run_validation_batch_001b.py` | Existing runner that can emit planned rows or execute configured `model_rerun` cases when `--execute` is supplied. |
| `modules/validation/batch_001b.py` | Existing config parsing, forced-port handling, maritime-distance override handling, unit conversion, record-only rows, and output writing. |
| `docs/validation/tf_validation_batch_001b_sensitivity_config.json` | Existing sensitivity config with only three `model_rerun` sensitivity rows plus record-only/planned audit rows. |
| `docs/validation/tf_validation_batch_001b_sensitivity_output.csv` and `.json` | Existing tracked numerical output artifacts used for the result tables below. |
| `docs/validation/tf_validation_batch_001b_sensitivity_results.md` | Existing run manifest and detailed execution record for the sensitivity output artifacts. |

The successful sensitivity command already recorded in the tracked run manifest was:

```powershell
.\venv\Scripts\python.exe scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_sensitivity_config.json --execute --output-csv docs/validation/tf_validation_batch_001b_sensitivity_output.csv --output-json docs/validation/tf_validation_batch_001b_sensitivity_output.json
```

That tracked run wrote three `executed` / `sensitivity_executed` rows, three blocked planned rows, and two record-only/excluded rows. This issue does not rerun the command, because the numerical artifacts are already tracked and rerunning would risk changing validation outputs through local cache, provider, or data-environment differences.

## 3. Sensitivity Scope And Parameters

The executable issue #16 scope is intentionally compact. It tests only documented maritime-distance and explicit alternate-port assumptions already accepted by the Batch 001B methodology decision layer.

| Parameter | Baseline value or source | Sensitivity value | Unit | Rationale | Affects | Type | Issue #16 status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Santos/Manaus maritime distance | Original Batch 001 fallback `2744.7 km`, source `SeaMatrix haversine fallback`. | `3300 nm` / `6111.6 km` documented for Santos/Manaus in the tracked external-reference summary. | km and nm | The fallback maritime distance materially understated the documented reference-distance candidate. | Cost and TTW CO2e. | Validation assumption. | Executed as reference-distance sensitivity. |
| Manaus/Fortaleza-region alternate port | Original selected-port row used Porto de Fortaleza, with fallback maritime distance `2391.2 km`. | Forced `BRPEC` / Pecem and `1569 nm` / `2905.788 km` for Manaus/Pecem. | port code, km, nm | Pecem is a documented nearby-port comparator, but it is not Porto de Fortaleza. | Cost, TTW CO2e, road access, and interpretation boundary. | Validation assumption and alternate-port boundary. | Executed as alternate-port sensitivity only. |
| Rio Grande/Recife-region alternate port | Original selected-port row used Porto do Recife, with fallback maritime distance `3214.0 km`. | Forced `BRSUA` / Suape and `1844 nm` / `3415.088 km` for Rio Grande/Suape. | port code, km, nm | Suape is a documented Pernambuco alternate-port comparator, but it is not Porto do Recife. | Cost, TTW CO2e, road access, and interpretation boundary. | Validation assumption and alternate-port boundary. | Executed as alternate-port sensitivity only. |
| Cargo mass / TEU assumption | Batch 001B default `14.0 t` and `1.0 TEU`. | No low/high value executed in this issue. | t and TEU | The current handoff does not define source-supported low/high cargo or load-factor cases for these three sensitivity rows. | Cost and TTW CO2e. | Model parameter. | `not_run_tooling_gap`: no tracked named Batch 001B sensitivity scenario. |
| Port operations and hoteling | Batch 001B defaults include port operations, `include_hoteling=true`, `hoteling_hours_per_call=14.0`, and `port_calls=2`; separate hoteling may be skipped by the evaluator when transport-work intensity already covers operational fuel. | No alternate port-ops or hoteling value executed in this issue. | hours, calls, boolean, scenario name | Changing this safely requires a specific double-counting and boundary decision per row. | Cost and TTW CO2e where included. | Model parameter and interpretation boundary. | `not_run_tooling_gap`: not part of the tracked eligible sensitivity config. |
| Truck fuel consumption / road intensity | Runtime road fuel model and `semi_27t` truck preset. | No low/high truck-efficiency value executed in this issue. | model preset / fuel intensity | The current issue is scoped to maritime-distance and alternate-port assumptions, not truck calibration. | Road cost and road TTW CO2e. | Model parameter. | `not_run_tooling_gap`: no approved Batch 001B scenario bounds. |
| Maritime fuel intensity / vessel assumption | Batch 001B default `container_feeder`, `allocation_mode=auto`, `allocation_load_factor=0.8`. | No low/high maritime-intensity value executed in this issue. | vessel class / allocation parameter | No source-supported low/high maritime-intensity cases are defined for this issue. | Maritime cost and maritime TTW CO2e. | Model parameter. | `not_run_tooling_gap`: not part of the tracked eligible sensitivity config. |
| Cost-boundary assumptions | Existing model cost estimate boundary: fuel and represented operational components, not full commercial freight rates. | No wider freight-rate, tariff, time, reliability, or inventory-cost case executed. | BRL / boundary label | The repository does not contain source-supported full-rate adders for these sensitivity rows. | Cost only. | Interpretation boundary. | `not_run_tooling_gap`: future cost-boundary issue required. |

## 4. Executed Sensitivity Result Table

The table below reports only tracked executed sensitivity rows. Cost and emissions are per shipment. Emissions are operational TTW CO2e under the current model boundary. Costs are model cost estimates and must not be read as full commercial freight rates.

| Case ID | Sensitivity role | OD pair | Selected / forced ports | Maritime distance source and source type | Scenario name | Parameter varied | Baseline value | Sensitivity value | Cost direction or result | Emissions direction or result | Interpretation | Safe thesis wording |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | Santos/Manaus reference-distance sensitivity | Sao Paulo, SP -> Manaus, AM | Forced `BRSSZ` / Porto de Santos -> forced `BRMAO` / Porto de Manaus | Tracked external-reference summary; `external_reference` | Reference-distance sensitivity | Maritime distance | Original fallback `2744.7 km` from `SeaMatrix haversine fallback` | `3300 nm` / `6111.6 km` | Multimodal remains lower in the executed sensitivity row: road `BRL 18456.45`, multimodal `BRL 1263.50`, modeled savings `93.2%`. | Multimodal remains lower in the executed sensitivity row: road `6961.76 kg CO2e`, multimodal `1104.67 kg CO2e`, modeled reduction `84.1%`. | `sensitive` | Under the documented Santos/Manaus reference-distance sensitivity, the modeled multimodal option remains lower-cost and lower-TTW-CO2e than road-only, but the magnitude is distance-sensitive and is not a validated baseline conclusion. |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | Pecem alternate-port sensitivity | Manaus, AM -> Fortaleza, CE | Forced `BRMAO` / Porto de Manaus -> forced `BRPEC` / Pecem | Tracked external-reference summary; `external_reference` | Alternate-port sensitivity | Destination port and maritime distance | Original selected-port row used Porto de Fortaleza and fallback `2391.2 km` | Forced Pecem with `1569 nm` / `2905.788 km` | Multimodal remains lower in the executed alternate-port row: road `BRL 26391.03`, multimodal `BRL 727.33`, modeled savings `97.2%`. | Multimodal remains lower in the executed alternate-port row: road `9989.83 kg CO2e`, multimodal `573.48 kg CO2e`, modeled reduction `94.3%`. | `sensitive` | Under the Pecem alternate-port scenario, the modeled multimodal option is favorable, but this is not Porto de Fortaleza validation and must remain an alternate-port sensitivity discussion. |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | Suape alternate-port sensitivity | Porto Alegre, RS -> Recife, PE | Forced `BRRIG` / Porto do Rio Grande -> forced `BRSUA` / Suape | Tracked external-reference summary; `external_reference` | Alternate-port sensitivity | Destination port and maritime distance | Original selected-port row used Porto do Recife and fallback `3214.0 km` | Forced Suape with `1844 nm` / `3415.088 km` | Multimodal remains lower in the executed alternate-port row: road `BRL 18121.99`, multimodal `BRL 2122.38`, modeled savings `88.3%`. | Multimodal remains lower in the executed alternate-port row: road `7013.27 kg CO2e`, multimodal `1127.46 kg CO2e`, modeled reduction `83.9%`. | `sensitive` | Under the Suape alternate-port scenario, the modeled multimodal option is favorable, but this is not Porto do Recife validation and must remain an alternate-port sensitivity discussion. |

## 5. Directional Interpretation

All three executed sensitivity rows preserve the same modeled direction under the current operational boundary: multimodal road-cabotage-road is lower than road-only for both model cost estimate and operational TTW CO2e.

That directional result is not enough for `robust` classification because:

- only one documented sensitivity value was executed for each eligible row;
- the runs do not test cargo mass / TEU, truck fuel consumption, maritime fuel intensity, hoteling, port operations, or cost-boundary expansion;
- the Pecem and Suape rows are alternate-port scenarios, not exact selected-port validation;
- cost outputs remain model cost estimates rather than full freight rates;
- emissions outputs remain operational TTW CO2e and must not be mixed with WTW or LCA claims.

Final classification for issue #16:

| Case | Classification | Reason |
| --- | --- | --- |
| `TF-VAL-001B-SENS-002-REFDIST` | `sensitive` | The modeled direction remains favorable after applying the documented reference distance, but the magnitude changes under a material maritime-distance correction and the row is not a validated baseline. |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | `sensitive` | The modeled direction is favorable only under an explicit Pecem alternate-port scenario; it cannot validate Porto de Fortaleza. |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | `sensitive` | The modeled direction is favorable only under an explicit Suape alternate-port scenario; it cannot validate Porto do Recife. |

No Batch 001B sensitivity row is classified as `robust` for headline thesis conclusions.

The original selected-port Fortaleza and Recife claims remain `inconclusive` for numerical thesis conclusions because the executed rows use Pecem and Suape alternate ports, respectively. They should be resolved only through exact selected-port references or a later methodology decision.

## 6. Cases excluded from issue #16

| Case | Exclusion reason | Required before future sensitivity analysis |
| --- | --- | --- |
| `TF-VAL-001B-001` | Same-port Sao Paulo -> Santos row is a warning/exclusion record, not a meaningful cabotage corridor. | A future model-boundary decision would be needed to study local same-port route behavior; it should not be a normal cabotage sensitivity case. |
| `TF-VAL-001B-003A` | Exact Porto de Manaus -> Porto de Fortaleza maritime distance/source remains missing. Pecem cannot be substituted into this selected-port row. | Add exact selected-port distance/source evidence and preserve unit/provenance before any execution. |
| `TF-VAL-001B-004A` | Original Angra dos Reis -> Salvador chain is invalid/excluded for the current 1 TEU / 14 t container benchmark. | A different defensible origin-port methodology or cargo boundary would be needed; the original Angra dos Reis chain should remain excluded. |
| `TF-VAL-001B-004B` | No defensible alternate origin port and no alternate-origin maritime distance/source are documented for Brasilia -> Salvador. | Select and document a defensible alternate origin port, distance source, unit, and provenance. |
| `TF-VAL-001B-005A` | Exact Porto do Rio Grande -> Porto do Recife maritime distance/source remains missing. Suape cannot be substituted into this selected-port row. | Add exact selected-port distance/source evidence and preserve unit/provenance before any execution. |

## 7. Implications for final thesis text

Findings robust enough for the Results section:

- None as headline conclusions. The executed rows are sensitivity evidence only.
- The Results section may report that the three named sensitivity scenarios were executed and that, under the current TTW CO2e and model-cost boundary, the modeled multimodal option remains lower than road-only in those rows. This statement must be labeled as sensitivity output, not validated baseline evidence.

Findings that belong in sensitivity or discussion:

- Santos/Manaus: the reference-distance sensitivity can be used to show that replacing the fallback distance still leaves a modeled multimodal advantage, but the magnitude is sensitive to maritime distance and cost-boundary assumptions.
- Manaus/Fortaleza region: the Pecem scenario can be discussed only as an alternate-port sensitivity, with explicit separation from Porto de Fortaleza.
- Porto Alegre/Recife region: the Suape scenario can be discussed only as an alternate-port sensitivity, with explicit separation from Porto do Recife.

Findings that belong only in limitations:

- Same-port Santos/Santos behavior.
- Missing exact selected-port distances for Manaus/Fortaleza and Rio Grande/Recife.
- Invalid Angra dos Reis selected-port chain for the current container benchmark.
- Missing Brasilia/Salvador alternate-origin decision.
- Unrun cargo/load, truck fuel, maritime fuel intensity, hoteling, port-ops, and full cost-boundary sensitivities.

The thesis must not claim:

- that cabotage is universally better;
- that any sensitivity row is a validated baseline replacement;
- that Pecem is Porto de Fortaleza;
- that Suape is Porto do Recife;
- that model cost estimates are commercial freight rates;
- that TTW CO2e results are WTW or LCA results;
- that blocked or excluded cases were numerically interpreted in issue #16.
