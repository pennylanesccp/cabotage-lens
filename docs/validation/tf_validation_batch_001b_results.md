# TF Validation Batch 001B Results

Original planned export date: 2026-06-26

Schema refresh date: 2026-06-27

Original planned export commit SHA: `2c68d8bcc6d34bac8151dea3e4ae67527f9e899e`

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

The CSV and JSON artifacts were refreshed on 2026-06-27 in non-executing mode so their fields align with the current `ALL_OUTPUT_FIELDS` schema, including maritime distance unit, normalized source type, notes, optional bounds, and original maritime source type.

The methodology-decision layer for these rows is recorded in `docs/validation/tf_validation_batch_001b_methodology_decisions.md`.

The thesis-ready issue #16 sensitivity summary is recorded in `docs/validation/tf_sensitivity_results_batch_001b.md`.

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

The current schema refresh was run with the local virtual environment:

```powershell
.\venv\Scripts\python.exe scripts\run_validation_batch_001b.py --config docs\validation\tf_validation_batch_001b_config.json
```

Result: success. The runner rewrote the planned CSV and JSON artifacts with `rows=8` and `execute=False`.

The actual execution command was not run:

```powershell
py scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_config.json --execute
```

Reason: there were no `ready_to_execute` model cases. Running `--execute` would force blocked cases through the model, which would conflict with the Batch 001B rule that missing assumptions must not be converted into artificial outputs.

## 3. Artifact Status And Methodology Classification

The readiness table below records the non-executing Batch 001B artifact/export status at the time the CSV/JSON were generated. The later methodology-decision layer in `tf_validation_batch_001b_methodology_decisions.md` determines issue #16 eligibility. In that later layer, selected blocked-methodology rows may be promoted only to named sensitivity analysis, not to validated baseline or headline thesis conclusions.

| Case ID | Original case | OD pair | Artifact readiness | Execution mode | Output status | Artifact validation status | Methodology-decision status | Issue #16 use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001` | Sao Paulo, SP -> Santos, SP | `record_only` | `record_only` | `record_only` | `warning_only` | `record_only_warning` | Excluded from numerical issue #16 execution; same-port route-logic limitation only. |
| `TF-VAL-001B-002` | `TF-VAL-002` | Sao Paulo, SP -> Manaus, AM | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | `sensitivity_only` | Eligible only as Santos/Manaus reference-distance sensitivity; not a validated baseline replacement. |
| `TF-VAL-001B-003A` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE | `blocked_reference_needed` | `planned` | `planned` | `blocked_reference_needed` | `reference_needed` | Blocked unless exact Porto de Manaus -> Porto de Fortaleza evidence is added. |
| `TF-VAL-001B-003B` | `TF-VAL-003` | Manaus, AM -> Fortaleza, CE with Pecem alternate port | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | `sensitivity_only` | Eligible only as Pecem alternate-port sensitivity; not Fortaleza selected-port validation. |
| `TF-VAL-001B-004A` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA | `record_only` | `record_only` | `record_only` | `excluded` | `excluded` | Excluded from issue #16 execution; invalid Angra dos Reis container chain. |
| `TF-VAL-001B-004B` | `TF-VAL-004` | Brasilia, DF -> Salvador, BA with alternate origin port | `blocked_missing_port` | `planned` | `planned` | `blocked_missing_port` | `planned_blocked_methodology_decision` | Blocked unless a defensible alternate origin port and distance source are documented. |
| `TF-VAL-001B-005A` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE | `blocked_reference_needed` | `planned` | `planned` | `blocked_reference_needed` | `reference_needed` | Blocked unless exact Porto do Rio Grande -> Porto do Recife evidence is added. |
| `TF-VAL-001B-005B` | `TF-VAL-005` | Porto Alegre, RS -> Recife, PE with Suape alternate port | `blocked_methodology_decision` | `planned` | `planned` | `blocked_methodology_decision` | `sensitivity_only` | Eligible only as Suape alternate-port sensitivity; not Recife selected-port validation. |

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

Artifact note: at export time, this row remained `blocked_methodology_decision`. The later methodology-decision layer classifies it as `sensitivity_only` for a named reference-distance sensitivity.

Thesis use: not a validated numerical result, baseline replacement, or headline conclusion. Use only as Santos/Manaus reference-distance sensitivity.

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

Artifact note: at export time, this row remained `blocked_methodology_decision`. The later methodology-decision layer classifies it as `sensitivity_only` for a named Pecem alternate-port sensitivity.

Thesis use: alternate-port sensitivity only. It must not be presented as the Fortaleza selected-port case, a validated baseline replacement, or a headline conclusion.

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

Artifact note: at export time, this row remained `blocked_methodology_decision`. The later methodology-decision layer classifies it as `sensitivity_only` for a named Suape alternate-port sensitivity.

Thesis use: alternate-port sensitivity only. It must not be presented as the Recife selected-port case, a validated baseline replacement, or a headline conclusion.

## 5. Validation Implications

Batch 001B did not validate any new cost, emissions, or road-sea-road advantage conclusion.

The artifacts are useful because they now separate:

- same-port and invalid-port records that can be emitted without rerun;
- documented maritime-distance candidates that still need methodology decisions;
- exact selected-port cases that remain reference-blocked;
- alternate-port candidates that must remain explicitly labeled.

The planned rows are suitable as an audit trail and sensitivity setup, not as final thesis results.

## 6. Handoff For Issue #16 Sensitivity Analysis

Issue #16 should not start by running every planned row. It should follow the methodology-decision layer in `docs/validation/tf_validation_batch_001b_methodology_decisions.md`.

Eligible rows are limited to:

- `TF-VAL-001B-002`: reference-distance sensitivity using the documented Santos/Manaus `3300 nm` candidate.
- `TF-VAL-001B-003B`: Pecem alternate-port sensitivity only; not Porto de Fortaleza validation.
- `TF-VAL-001B-005B`: Suape alternate-port sensitivity only; not Porto do Recife validation.

The following remain excluded or blocked for issue #16 unless later evidence or methodology changes: `TF-VAL-001B-001`, `TF-VAL-001B-003A`, `TF-VAL-001B-004A`, `TF-VAL-001B-004B`, and `TF-VAL-001B-005A`.

Sensitivity reruns should be executed only for rows whose config can be changed from `planned` to `model_rerun` without adding undocumented assumptions. Sensitivity outputs are not validated baselines and must not be used as headline thesis conclusions.
