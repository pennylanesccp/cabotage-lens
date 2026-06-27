# Batch 001B Sensitivity Results

Execution date: 2026-06-26

Git commit SHA at run time: `e770f4694a6aca6c73556027dadacff7df25bac5`

Working-tree note: this sensitivity run used the issue #16 local changes that allow mixed configs to retain blocked rows as planned during `--execute`.

Decision source: `docs/validation/tf_validation_batch_001b_sensitivity_decisions.md`

Config source: `docs/validation/tf_validation_batch_001b_sensitivity_config.json`

Output artifacts:

- `docs/validation/tf_validation_batch_001b_sensitivity_output.csv`
- `docs/validation/tf_validation_batch_001b_sensitivity_output.json`

## 1. Execution Summary

The sensitivity artifact was generated in planned mode. Actual model execution was attempted for the sensitivity-ready rows, but no numerical sensitivity scenario was executed because the active local Python environment is missing the runtime dependency `pandas`.

Final artifact status:

- 8 rows included;
- 2 record-only/excluded rows;
- 3 blocked planned rows;
- 3 sensitivity-ready planned rows;
- 0 sensitivity-executed rows.

The CSV/JSON output files remain planned review artifacts. They do not contain cost or emissions results.

## 2. Commands Run

Planned sensitivity output:

```powershell
py scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_sensitivity_config.json --output-csv docs/validation/tf_validation_batch_001b_sensitivity_output.csv --output-json docs/validation/tf_validation_batch_001b_sensitivity_output.json
```

Result: success. The runner wrote 8 rows with `execute=False`.

Actual sensitivity execution attempt:

```powershell
py scripts/run_validation_batch_001b.py --config docs/validation/tf_validation_batch_001b_sensitivity_config.json --execute --output-csv docs/validation/tf_validation_batch_001b_sensitivity_output.csv --output-json docs/validation/tf_validation_batch_001b_sensitivity_output.json
```

Result: failed before routing or evaluation because `modules.costs.diesel_prices` imports `pandas`, and `pandas` is not installed in the active `py` environment.

The repository did not have `.\\venv\\Scripts\\python.exe`, so no project virtual environment was available for a second execution attempt.

## 3. Cases Included

| Case ID | Original Batch 001B case | Original Batch 001 case | Type | Output status | Sensitivity / validation status | Execution outcome |
| --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `TF-VAL-001B-001` | `TF-VAL-001` | record-only same-port case | `record_only` | `record_only` | emitted; not executed |
| `TF-VAL-001B-SENS-002-REFDIST` | `TF-VAL-001B-002` | `TF-VAL-002` | reference-distance sensitivity | `planned` | `sensitivity_ready` | `not_executed_environment` |
| `TF-VAL-001B-003A` | `TF-VAL-001B-003A` | `TF-VAL-003` | exact selected-port audit row | `planned` | `blocked_reference_needed` | not executed |
| `TF-VAL-001B-SENS-003B-ALTPECEM` | `TF-VAL-001B-003B` | `TF-VAL-003` | alternate-port sensitivity | `planned` | `sensitivity_ready` | `not_executed_environment` |
| `TF-VAL-001B-004A` | `TF-VAL-001B-004A` | `TF-VAL-004` | invalid/excluded case | `record_only` | `excluded` | emitted; not executed |
| `TF-VAL-001B-004B` | `TF-VAL-001B-004B` | `TF-VAL-004` | alternate-origin audit row | `planned` | `blocked_missing_port` | not executed |
| `TF-VAL-001B-005A` | `TF-VAL-001B-005A` | `TF-VAL-005` | exact selected-port audit row | `planned` | `blocked_reference_needed` | not executed |
| `TF-VAL-001B-SENS-005B-ALTSUAPE` | `TF-VAL-001B-005B` | `TF-VAL-005` | alternate-port sensitivity | `planned` | `sensitivity_ready` | `not_executed_environment` |

## 4. Sensitivity Scenarios

### `TF-VAL-001B-SENS-002-REFDIST`

Original Batch 001B case ID: `TF-VAL-001B-002`

Original Batch 001 case ID: `TF-VAL-002`

OD pair: Sao Paulo, SP -> Manaus, AM

Selected or forced ports: forced `BRSSZ` / Santos -> forced `BRMAO` / Manaus.

Maritime distance used in planned sensitivity row: `3300 nm` / `6111.6 km`.

Original maritime distance preserved: `2744.7 km`, source `SeaMatrix haversine fallback`.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRMAO -> BRSSZ.

Execution status: `not_executed_environment`.

Cost/emissions fields: not populated.

Thesis use: planned reference-distance sensitivity only. It can test sensitivity to replacing the fallback distance after execution is possible. It cannot be used as a validated baseline result.

### `TF-VAL-001B-SENS-003B-ALTPECEM`

Original Batch 001B case ID: `TF-VAL-001B-003B`

Original Batch 001 case ID: `TF-VAL-003`

OD pair: Manaus, AM -> Fortaleza, CE, with Pecem as explicit alternate destination port.

Selected or forced ports: forced `BRMAO` / Manaus -> forced `BRPEC` / Pecem.

Maritime distance used in planned sensitivity row: `1569 nm` / `2905.788 km`.

Original maritime distance preserved: `2391.2 km`, source `SeaMatrix haversine fallback` for the original Manaus -> Fortaleza selected-port row.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRMAO -> BRPEC.

Execution status: `not_executed_environment`.

Cost/emissions fields: not populated.

Thesis use: planned alternate-port sensitivity only. It must not be presented as a Porto de Fortaleza result. The runner can represent road access transparently through the forced destination port when the environment can execute.

### `TF-VAL-001B-SENS-005B-ALTSUAPE`

Original Batch 001B case ID: `TF-VAL-001B-005B`

Original Batch 001 case ID: `TF-VAL-005`

OD pair: Porto Alegre, RS -> Recife, PE, with Suape as explicit alternate destination port.

Selected or forced ports: forced `BRRIG` / Rio Grande -> forced `BRSUA` / Suape.

Maritime distance used in planned sensitivity row: `1844 nm` / `3415.088 km`.

Original maritime distance preserved: `3214.0 km`, source `SeaMatrix haversine fallback` for the original Rio Grande -> Recife selected-port row.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, based on Costa et al. (2025), Appendix 6, ANTAQ-based matrix, BRRIG -> BRSUA.

Execution status: `not_executed_environment`.

Cost/emissions fields: not populated.

Thesis use: planned alternate-port sensitivity only. It must not be presented as a Porto do Recife result. The runner can represent road access transparently through the forced destination port when the environment can execute.

## 5. Blocked Rows

`TF-VAL-001B-003A` remains `blocked_reference_needed` because exact Porto de Manaus -> Porto de Fortaleza maritime distance/source is not documented.

`TF-VAL-001B-004B` remains `blocked_missing_port` because no defensible alternate origin port and distance rule are documented for Brasilia -> Salvador.

`TF-VAL-001B-005A` remains `blocked_reference_needed` because exact Porto do Rio Grande -> Porto do Recife maritime distance/source is not documented.

These rows were not executed and must not be interpreted as sensitivity results.

## 6. Interpretation Limits

No cost or emissions comparison changed as a result of this issue because no sensitivity scenario executed numerically.

The current artifacts support only the following thesis statements:

- A sensitivity setup now exists for Santos -> Manaus using the documented `3300 nm` reference-distance candidate.
- Pecem and Suape are represented only as explicit alternate-port sensitivity scenarios, not as replacements for Fortaleza or Recife.
- Exact Fortaleza and Recife selected-port cases remain blocked.
- Brasilia -> Salvador remains excluded or blocked until a defensible alternate origin port is selected.
- The final thesis should not classify these sensitivity rows as robust, validated, or baseline results until a dependency-complete execution environment produces numerical outputs.

## 7. Implications For Final Classification

Under `docs/tf_result_classification_rules.md`, these rows remain outside robust result classes:

- record-only and excluded rows should map to out-of-scope / invalid or route-logic limitation treatment;
- blocked rows should remain unvalidated or out-of-scope for numerical comparison;
- planned sensitivity rows can become sensitive-result evidence only after successful execution and review;
- alternate-port rows must be segregated from original selected-port validation tables.

## 8. Next Steps For Issue #17

Issue #17 should consolidate final thesis tables only after deciding how to handle the current non-executed sensitivity rows. Recommended next actions:

1. Prepare a dependency-complete execution environment, preferably the project virtual environment installed from `requirements.txt`.
2. Re-run the same sensitivity config with `--execute`.
3. Review whether the three sensitivity rows produce cost/emissions results and preserve forced-port and maritime-distance provenance.
4. Keep exact Fortaleza, exact Recife, and Brasilia alternate-origin rows blocked unless new documented evidence is added.
5. Build final tables with separate sections for validated baseline rows, record-only/excluded rows, blocked rows, and sensitivity/alternate-port rows.
