# Batch 001B Sensitivity Results

Execution date: 2026-06-27

Git commit SHA at run time: `2dd86de22cde3935765ea60fa072a34bc678d78b`

Working-tree note: the rerun used the committed Batch 001B sensitivity runner and config, plus local validation data assets restored or generated from documented project sources. A project virtual environment installed from `requirements.txt` was used.

Decision source: `docs/validation/tf_validation_batch_001b_sensitivity_decisions.md`

Config source: `docs/validation/tf_validation_batch_001b_sensitivity_config.json`

Output artifacts:

- `docs/validation/tf_validation_batch_001b_sensitivity_output.csv`
- `docs/validation/tf_validation_batch_001b_sensitivity_output.json`

## 1. Execution Summary

Actual sensitivity execution completed for the three sensitivity-ready rows. The run wrote 8 output rows:

- 2 record-only/excluded rows;
- 3 executed sensitivity rows;
- 3 blocked planned rows;
- 0 failed executed rows.

The executed rows are sensitivity results only. They are not validated baseline results and must remain separate from the original Batch 001 outputs and from any final thesis baseline table.

The configured Supabase Postgres cache endpoint was still unavailable in this local environment. Road cache reads and writes failed with tenant/user lookup errors, but those failures were non-fatal; the runner continued with provider-returned in-memory route results. Supabase Storage was not required for fuel data after local data assets were present.

## 2. Local Data Boundary

The sensitivity run used local fuel-price files so that execution did not depend on unavailable Supabase Storage.

| Asset | Local path | Source/provenance | Units | Boundary note |
| --- | --- | --- | --- | --- |
| Road diesel price table | `data/processed/road_data/latest_diesel_prices.csv` | Generated with `modules.costs.diesel_price_updater` from the ANP weekly state fuel-price workbook. The generated table contains 27 UF rows for `OLEO DIESEL S10`; the ANP workbook latest `DATA FINAL` inspected for those rows was 2026-06-27. | `price` in BRL/L by `UF` | Official fuel-price table, but the processed CSV preserves only `UF` and `price`, not the date column. The date is documented here for this run. |
| Maritime bunker price | `data/processed/maritime_fuel/santos_bunker_brl.txt` | Restored as a local replay input from `docs/validation/tf_validation_batch_001_results.md` and `docs/validation/tf_validation_batch_001_external_references.md`, which document the Batch 001 runtime input as Santos VLSFO, BRL 2572.34/mt, date 2025-11-17. | BRL/mt | This is not a new independent bunker-price validation. It preserves the documented Batch 001 fuel-cost boundary so the sensitivity rows can execute reproducibly without Supabase Storage. |

No new diesel price, bunker price, emissions factor, vessel parameter, port choice, or maritime distance was invented for this run.

## 3. Commands Run

Local diesel-price asset generation:

```powershell
.\venv\Scripts\python.exe -m modules.costs.diesel_price_updater
```

Focused checks in the virtual environment:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_validation_batch_001b
.\venv\Scripts\python.exe -m compileall scripts modules
```

Actual sensitivity execution:

```powershell
.\venv\Scripts\python.exe scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_sensitivity_config.json --execute --output-csv docs/validation/tf_validation_batch_001b_sensitivity_output.csv --output-json docs/validation/tf_validation_batch_001b_sensitivity_output.json
```

Result: success. The runner wrote the CSV and JSON artifacts with three `executed` / `sensitivity_executed` rows.

An earlier execution attempt in the same environment failed after the diesel blocker was resolved because `data/processed/maritime_fuel/santos_bunker_brl.txt` was also missing and Supabase Storage was unavailable. The successful run occurred after restoring that documented local replay input.

## 4. Cases Included

| Case ID | Original Batch 001B case | Original Batch 001 case | Type | Output status | Sensitivity / validation status | Execution outcome |
| --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001B-001` | `TF-VAL-001` | record-only same-port case | `record_only` | `record_only` | emitted; not executed |
| `TF-VAL-001B-SENS-002-REFDIST` | `TF-VAL-001B-002` | `TF-VAL-002` | reference-distance sensitivity | `executed` | `sensitivity_executed` | executed with documented 3300 nm sensitivity distance |
| `TF-VAL-001B-003A` | `TF-VAL-001B-003A` | `TF-VAL-003` | exact selected-port audit row | `planned` | `blocked_reference_needed` | not executed |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | `TF-VAL-001B-003B` | `TF-VAL-003` | alternate-port sensitivity | `executed` | `sensitivity_executed` | executed as Pecem alternate-port scenario only |
| `TF-VAL-001B-004A` | `TF-VAL-001B-004A` | `TF-VAL-004` | invalid/excluded case | `record_only` | `excluded` | emitted; not executed |
| `TF-VAL-001B-004B` | `TF-VAL-001B-004B` | `TF-VAL-004` | alternate-origin audit row | `planned` | `blocked_missing_port` | not executed |
| `TF-VAL-001B-005A` | `TF-VAL-001B-005A` | `TF-VAL-005` | exact selected-port audit row | `planned` | `blocked_reference_needed` | not executed |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | `TF-VAL-001B-005B` | `TF-VAL-005` | alternate-port sensitivity | `executed` | `sensitivity_executed` | executed as Suape alternate-port scenario only |

## 5. Executed Sensitivity Scenarios

### `TF-VAL-001B-SENS-002-REFDIST`

Original Batch 001B case ID: `TF-VAL-001B-002`

Original Batch 001 case ID: `TF-VAL-002`

OD pair: Sao Paulo, SP -> Manaus, AM

Selected or forced ports: forced `BRSSZ` / Porto de Santos -> forced `BRMAO` / Porto de Manaus.

Maritime distance used: `3300 nm` / `6111.6 km`.

Original maritime distance preserved for comparison: `2744.7 km`, source `SeaMatrix haversine fallback`.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRMAO -> BRSSZ.

Execution status: `executed`; validation status `sensitivity_executed`.

Numerical outputs:

| Field | Value |
| --- | ---: |
| Road-only distance | 3883.5186 km |
| Pre-carriage distance | 84.6089 km |
| On-carriage distance | 22.2574 km |
| Road-only cost | BRL 18456.45 |
| Multimodal cost | BRL 1263.50 |
| Road-only emissions | 6961.76 kg CO2e |
| Multimodal emissions | 1104.67 kg CO2e |

Thesis use: reference-distance sensitivity only. It tests sensitivity to replacing the SeaMatrix haversine fallback with the documented ANTAQ-based distance candidate. It should not be treated as a validated baseline replacement unless the thesis separately justifies that classification.

### `TF-VAL-001B-SENS-003B-ALTPECEM`

Original Batch 001B case ID: `TF-VAL-001B-003B`

Original Batch 001 case ID: `TF-VAL-003`

OD pair: Manaus, AM -> Fortaleza, CE, with Pecem as explicit alternate destination port.

Selected or forced ports: forced `BRMAO` / Porto de Manaus -> forced `BRPEC` / Porto do Pecem.

Maritime distance used: `1569 nm` / `2905.788 km`.

Original maritime distance preserved for comparison: `2391.2 km`, source `SeaMatrix haversine fallback` for the original Manaus -> Fortaleza selected-port row.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRMAO -> BRPEC.

Execution status: `executed`; validation status `sensitivity_executed`.

Numerical outputs:

| Field | Value |
| --- | ---: |
| Road-only distance | 5572.6823 km |
| Pre-carriage distance | 22.1948 km |
| On-carriage distance | 51.7574 km |
| Road-only cost | BRL 26391.03 |
| Multimodal cost | BRL 727.33 |
| Road-only emissions | 9989.83 kg CO2e |
| Multimodal emissions | 573.48 kg CO2e |

Thesis use: alternate-port sensitivity only. It must not be presented as a Porto de Fortaleza result. The output can support discussion of a Pecem alternate-port scenario, including its modeled road-access implications, under the documented sensitivity assumptions.

### `TF-VAL-001B-SENS-005B-ALTSUAPE`

Original Batch 001B case ID: `TF-VAL-001B-005B`

Original Batch 001 case ID: `TF-VAL-005`

OD pair: Porto Alegre, RS -> Recife, PE, with Suape as explicit alternate destination port.

Selected or forced ports: forced `BRRIG` / Porto do Rio Grande -> forced `BRSUA` / Porto de Suape.

Maritime distance used: `1844 nm` / `3415.088 km`.

Original maritime distance preserved for comparison: `3214.0 km`, source `SeaMatrix haversine fallback` for the original Rio Grande -> Recife selected-port row.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRRIG -> BRSUA.

Execution status: `executed`; validation status `sensitivity_executed`.

Numerical outputs:

| Field | Value |
| --- | ---: |
| Road-only distance | 3912.2556 km |
| Pre-carriage distance | 325.1134 km |
| On-carriage distance | 49.1101 km |
| Road-only cost | BRL 18121.99 |
| Multimodal cost | BRL 2122.38 |
| Road-only emissions | 7013.27 kg CO2e |
| Multimodal emissions | 1127.46 kg CO2e |

Thesis use: alternate-port sensitivity only. It must not be presented as a Porto do Recife result. The output can support discussion of a Suape alternate-port scenario, including its modeled road-access implications, under the documented sensitivity assumptions.

## 6. Blocked Rows

`TF-VAL-001B-003A` remains `blocked_reference_needed` because exact Porto de Manaus -> Porto de Fortaleza maritime distance/source is not documented.

`TF-VAL-001B-004B` remains `blocked_missing_port` because no defensible alternate origin port and distance rule are documented for Brasilia -> Salvador.

`TF-VAL-001B-005A` remains `blocked_reference_needed` because exact Porto do Rio Grande -> Porto do Recife maritime distance/source is not documented.

These rows were not executed and must not be interpreted as sensitivity results.

## 7. Interpretation Limits

The executed rows provide numerical sensitivity evidence under the current model boundary and local fuel data boundary. They do not validate the original Batch 001 fallback distances, do not validate exact Fortaleza or Recife port-pair results, and do not validate total freight-rate cost.

The cost outputs remain energy-cost/model-boundary outputs. They use:

- road diesel prices by UF from the local ANP-derived Diesel S10 table;
- the restored Santos VLSFO BRL/mt replay input from Batch 001 validation logs;
- modeled road fuel, maritime fuel, and port-operation cost paths already implemented by the evaluator.

The emissions outputs remain model-boundary operational emissions estimates. The sensitivity run did not change emission factors, vessel allocation, cargo assumptions, or port-operation methodology.

Pecem and Suape rows are explicitly alternate-port scenarios. They must remain segregated from original selected-port validation rows and must not be described as silent replacements for Fortaleza or Recife.

## 8. Implications For Final Classification

Under `docs/tf_result_classification_rules.md`, the final thesis tables should classify these rows as follows:

- `TF-VAL-001B-SENS-002-REFDIST`: sensitivity result, not validated baseline.
- `TF-VAL-001B-SENS-003B-ALTPECEM`: alternate-port sensitivity result, not Fortaleza validation.
- `TF-VAL-001B-SENS-005B-ALTSUAPE`: alternate-port sensitivity result, not Recife validation.
- record-only and excluded rows: out-of-scope / invalid or warning-only validation outcomes.
- blocked rows: unresolved and excluded from numerical conclusion tables until their evidence gaps are closed.

The sensitivity rows can support thesis discussion of direction and magnitude under documented alternate assumptions, but final claims should keep validation, sensitivity, and alternate-port classifications separate.

## 9. Next Steps For Issue #17

Recommended issue #17 scope:

1. Consolidate final result tables with separate sections for validated baseline, record-only/excluded, blocked, and sensitivity/alternate-port rows.
2. Include the local fuel-data boundary in table notes, especially the ANP Diesel S10 date and the restored Santos VLSFO replay input.
3. Do not use exact Fortaleza, exact Recife, or Brasilia alternate-origin rows in numerical conclusion tables unless new documented evidence is added.
4. Decide whether the restored bunker-price replay input is sufficient for final thesis tables or whether a separate fuel-price sensitivity issue is needed for current Ship & Bunker and FX values.
5. Preserve the original Batch 001 outputs as the uncorrected execution record.
