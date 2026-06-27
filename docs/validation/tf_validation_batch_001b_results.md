# TF Validation Batch 001B Results

Execution date: 2026-06-26

Git commit SHA: `2c68d8bcc6d34bac8151dea3e4ae67527f9e899e`

Batch source config: `docs/validation/tf_validation_batch_001b_config.json`

Output artifacts:

- `docs/validation/tf_validation_batch_001b_output.csv`
- `docs/validation/tf_validation_batch_001b_output.json`

## 1. Execution Summary

Batch 001B was emitted in planned-only mode. No numerical model reruns were executed because no model-rerun case had all required assumptions documented and finalized.

The run produced eight artifact rows:

- 2 record-only rows;
- 6 planned/blocked rows;
- 0 executed model rows.

The planned rows preserve documented reference candidates where they already exist, but they are not presented as executed model results. Cost and emissions fields remain empty for every Batch 001B row because no model evaluation was performed.

Original Batch 001 outputs remain preserved in `docs/validation/tf_validation_batch_001_results.md`.

## 2. Commands Run

The requested command shape was attempted first:

```powershell
python scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_config.json
```

Result: failed before the project code ran because this Windows environment resolves `python` to the Microsoft Store app-execution alias.

The same planned-only run was then executed with the working Python launcher:

```powershell
py scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_config.json
```

Result: success. The runner wrote the CSV and JSON artifacts listed above with `rows=8` and `execute=False`.

The actual execution command was not run:

```powershell
py scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_config.json --execute
```

Reason: there were no `ready_to_execute` model cases. Running `--execute` would force blocked cases through the model, which would conflict with the Batch 001B rule that missing assumptions must not be converted into artificial outputs.

## 3. Readiness Classification

| Case ID | Original case | OD pair | Readiness | Execution mode | Output status | Validation status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | `record_only` | `record_only` | `record_only` | `warning_only` | Same-port / close-to-port case; cabotage-inappropriate for normal road-sea-road conclusions. |
| `TF-VAL-001B-002` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | Santos -> Manaus reference value is documented, but the replacement/bound/sensitivity rule is not finalized. |
| `TF-VAL-001B-003A` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | `blocked_reference_needed` | `planned` | `planned` | `blocked_reference_needed` | Exact Porto de Manaus -> Porto de Fortaleza maritime distance/source was not found in the existing evidence. |
| `TF-VAL-001B-003B` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE with Pecem alternate port | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | Pecem and reference distance are documented as an alternate candidate, but road access and Fortaleza-vs-Pecem thesis boundary are not finalized. |
| `TF-VAL-001B-004A` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | `record_only` | `record_only` | `record_only` | `excluded` | Original Angra dos Reis origin-port chain is invalid/excluded for the 1 TEU / 14 t container benchmark. |
| `TF-VAL-001B-004B` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA with alternate origin port | `blocked_missing_port` | `planned` | `planned` | `blocked_missing_port` | No defensible alternate origin port has been selected; the maritime distance rule is also missing. |
| `TF-VAL-001B-005A` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | `blocked_reference_needed` | `planned` | `planned` | `blocked_reference_needed` | Exact Porto do Rio Grande -> Porto do Recife maritime distance/source was not found in the existing evidence. |
| `TF-VAL-001B-005B` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE with Suape alternate port | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | Suape and reference distance are documented as an alternate candidate, but road access and Recife-vs-Suape thesis boundary are not finalized. |

## 4. Case Details

### `TF-VAL-001B-001`

Original case ID: `TF-VAL-001`

OD pair: Sao Paulo, SP -> Santos, SP

Selected/forced ports: `Porto de Santos` -> `Porto de Santos`; no forced ports.

Maritime distance status: original Batch 001 same-port sea leg `0.0 km`, with `SeaMatrix haversine fallback` preserved as original source.

Execution mode: record only.

Validation status: `warning_only`

Sensitivity required: false.

Thesis use: route-logic limitation only. This row supports same-port warning/exclusion logic, not a cabotage-performance conclusion.

### `TF-VAL-001B-002`

Original case ID: `TF-VAL-002`

OD pair: Sao Paulo, SP -> Manaus, AM

Selected/forced ports: `Porto de Santos` -> `Porto de Manaus`; no forced ports.

Maritime distance status: documented reference candidate `3300 nm` / `6111.6 km` from the existing external references. Original Batch 001 fallback distance `2744.7 km` is preserved.

Execution mode: planned only.

Validation status: `blocked_methodology_decision`

Sensitivity required: true.

Blocker: the existing docs document the ANTAQ-based reference value, but they do not yet define whether Batch 001B should use it as a single replacement, a bound, or a sensitivity scenario.

Thesis use: not a validated numerical result. Use only to define the next sensitivity input for Santos -> Manaus.

### `TF-VAL-001B-003A`

Original case ID: `TF-VAL-003`

OD pair: Manaus, AM -> Fortaleza, CE

Selected/forced ports: `Porto de Manaus` -> `Porto de Fortaleza`; no forced ports.

Maritime distance status: exact selected-port reference not documented. The original Batch 001 fallback distance `2391.2 km` is preserved as original output only.

Execution mode: planned only.

Validation status: `blocked_reference_needed`

Sensitivity required: true.

Blocker: exact Porto de Manaus -> Porto de Fortaleza distance/source was not found in the existing evidence.

Thesis use: unresolved model-selected-port case. Do not substitute Pecem here.

### `TF-VAL-001B-003B`

Original case ID: `TF-VAL-003`

OD pair: Manaus, AM -> Fortaleza, CE, with Pecem as an explicit alternate destination port.

Selected/forced ports: original selected ports were `Porto de Manaus` -> `Porto de Fortaleza`; forced alternate destination is `BRPEC`.

Maritime distance status: documented alternate-port reference candidate `1569 nm` / `2905.788 km` for `BRMAO` -> `BRPEC`. Original Batch 001 fallback distance `2391.2 km` is preserved.

Execution mode: planned only.

Validation status: `blocked_methodology_decision`

Sensitivity required: true.

Blocker: the Pecem alternate-port interpretation still needs an explicit thesis boundary decision and road access implications for Fortaleza versus Pecem before cost/emissions rerun.

Thesis use: possible future alternate-port sensitivity row only. It must not be presented as the Fortaleza selected-port case.

### `TF-VAL-001B-004A`

Original case ID: `TF-VAL-004`

OD pair: Brasilia, DF -> Salvador, BA

Selected/forced ports: `Porto de Angra dos Reis` -> `Porto de Salvador`; no forced ports.

Maritime distance status: original Batch 001 fallback distance `1273.3 km` is preserved as original output only.

Execution mode: record only.

Validation status: `excluded`

Sensitivity required: false.

Thesis use: route-logic and operational-plausibility failure. This row supports excluding the Angra dos Reis chain from thesis-supporting conclusions for the 1 TEU / 14 t benchmark.

### `TF-VAL-001B-004B`

Original case ID: `TF-VAL-004`

OD pair: Brasilia, DF -> Salvador, BA, with a future alternate origin port.

Selected/forced ports: original selected ports were `Porto de Angra dos Reis` -> `Porto de Salvador`; no forced alternate origin port has been selected.

Maritime distance status: missing because no alternate origin port exists yet.

Execution mode: planned only.

Validation status: `blocked_missing_port`

Sensitivity required: true.

Blocker: a defensible alternate origin port must be selected and documented before any corrected rerun can exist.

Thesis use: no quantitative use yet. This row documents the required alternate-port decision.

### `TF-VAL-001B-005A`

Original case ID: `TF-VAL-005`

OD pair: Porto Alegre, RS -> Recife, PE

Selected/forced ports: `Porto do Rio Grande` -> `Porto do Recife`; no forced ports.

Maritime distance status: exact selected-port reference not documented. The original Batch 001 fallback distance `3214.0 km` is preserved as original output only.

Execution mode: planned only.

Validation status: `blocked_reference_needed`

Sensitivity required: true.

Blocker: exact Porto do Rio Grande -> Porto do Recife distance/source was not found in the existing evidence.

Thesis use: unresolved model-selected-port case. Do not substitute Suape here.

### `TF-VAL-001B-005B`

Original case ID: `TF-VAL-005`

OD pair: Porto Alegre, RS -> Recife, PE, with Suape as an explicit alternate destination port.

Selected/forced ports: original selected ports were `Porto do Rio Grande` -> `Porto do Recife`; forced alternate destination is `BRSUA`.

Maritime distance status: documented alternate-port reference candidate `1844 nm` / `3415.088 km` for `BRRIG` -> `BRSUA`. Original Batch 001 fallback distance `3214.0 km` is preserved.

Execution mode: planned only.

Validation status: `blocked_methodology_decision`

Sensitivity required: true.

Blocker: the Suape alternate-port interpretation still needs an explicit thesis boundary decision and road access implications for Recife versus Suape before cost/emissions rerun.

Thesis use: possible future alternate-port sensitivity row only. It must not be presented as the Recife selected-port case.

## 5. Validation Implications

Batch 001B did not validate any new cost, emissions, or road-sea-road advantage conclusion.

The artifacts are useful because they now separate:

- same-port and invalid-port records that can be emitted without rerun;
- documented maritime-distance candidates that still need methodology decisions;
- exact selected-port cases that remain reference-blocked;
- alternate-port candidates that must remain explicitly labeled.

The planned rows are suitable as an audit trail and sensitivity setup, not as final thesis results.

## 6. Next Steps For Issue #16 Sensitivity Analysis

Issue #16 should not start by running every planned row. It should first resolve the sensitivity inputs:

1. Decide whether `TF-VAL-001B-002` uses `3300 nm` as a single replacement, one bound in a range, or one named sensitivity scenario.
2. Decide whether `TF-VAL-001B-003B` is an acceptable Pecem alternate-port scenario and document Pecem -> Fortaleza road-access treatment before execution.
3. Decide whether `TF-VAL-001B-005B` is an acceptable Suape alternate-port scenario and document Suape -> Recife road-access treatment before execution.
4. Select a defensible alternate origin port for `TF-VAL-001B-004B`, or keep the original Brasilia -> Salvador case excluded.
5. Keep `TF-VAL-001B-003A` and `TF-VAL-001B-005A` blocked unless exact Fortaleza and Recife selected-port references are collected.

After those decisions, reruns should be executed only for rows whose config can be changed from `planned` to `model_rerun` without adding undocumented assumptions.
