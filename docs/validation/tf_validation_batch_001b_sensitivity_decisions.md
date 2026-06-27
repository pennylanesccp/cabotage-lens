# Batch 001B Sensitivity Decisions

## 1. Purpose

This document defines which Batch 001B rows can be used for sensitivity analysis and which rows remain record-only, excluded, or blocked. It is a sensitivity decision layer, not a validation-status upgrade and not a replacement for the original Batch 001 results.

Sensitivity analysis here has a narrow purpose: test how corrected or alternate maritime-distance assumptions affect model outputs when the assumptions are already documented. It does not prove that a corridor is fully validated, and it does not turn alternate-port rows into the original selected-port case.

## 2. Interpretation Rules

Validation, sensitivity, and alternate-port scenarios are separate:

- Validation requires independently defensible route logic, port selection, distance source, service plausibility, and cost/emissions boundary compatibility.
- Sensitivity analysis tests a documented assumption change while keeping the limitation visible.
- Alternate-port sensitivity uses a different port than the original model-selected port and must be labeled as an alternate scenario.
- Record-only rows preserve methodological outcomes without numerical rerun.
- Blocked rows are retained only as audit trail rows and must not be forced through execution.

Controlled labels used in this issue:

- `excluded`
- `record_only`
- `blocked_reference_needed`
- `blocked_missing_port`
- `blocked_methodology_decision`
- `sensitivity_ready`
- `sensitivity_executed`
- `not_executed_environment`
- `not_executed_missing_assumption`

## 3. Case Decisions

| Batch 001B case | Decision label | Sensitivity case ID | Decision | Runnable assumption | Thesis use |
| --- | --- | --- | --- | --- | --- |
| `TF-VAL-001B-001` | `record_only` | none | Keep as same-port warning/exclusion. | None. Same-port cabotage is inappropriate for normal scenario execution. | Route-logic limitation only. |
| `TF-VAL-001B-002` | `sensitivity_ready` | `TF-VAL-001B-SENS-002-REFDIST` | Run a named reference-distance sensitivity for Santos -> Manaus. | Use `3300 nm` (`6111.6 km`) from the documented ANTAQ-based Costa et al. reference as a sensitivity distance, not as a validated baseline replacement. | Tests whether the Batch 001 conclusion is sensitive to replacing the SeaMatrix haversine fallback distance. |
| `TF-VAL-001B-003A` | `blocked_reference_needed` | none | Keep exact Manaus -> Fortaleza selected-port case blocked. | No exact Porto de Manaus -> Porto de Fortaleza distance/source is documented. | No thesis conclusion beyond identifying missing selected-port evidence. |
| `TF-VAL-001B-003B` | `sensitivity_ready` | `TF-VAL-001B-SENS-003B-ALTPECEM` | Run an explicit Pecem alternate-port sensitivity if the runner can compute road access from forced `BRPEC` to Fortaleza. | Use forced destination port `BRPEC` and `1569 nm` (`2905.788 km`) for BRMAO -> BRPEC from the documented reference. On-carriage is computed transparently by the runner from the forced port to the destination. | Alternate-port sensitivity only; must not be presented as Fortaleza. |
| `TF-VAL-001B-004A` | `excluded` | none | Keep Angra dos Reis -> Salvador as invalid/excluded. | None. Angra dos Reis is not defensible for the 1 TEU / 14 t container benchmark in the current evidence. | Operational-plausibility failure and exclusion record. |
| `TF-VAL-001B-004B` | `blocked_missing_port` | none | Keep Brasilia -> Salvador alternate-origin case blocked. | No defensible alternate origin port and no distance rule are documented. | No quantitative use. |
| `TF-VAL-001B-005A` | `blocked_reference_needed` | none | Keep exact Rio Grande -> Recife selected-port case blocked. | No exact Porto do Rio Grande -> Porto do Recife distance/source is documented. | No thesis conclusion beyond identifying missing selected-port evidence. |
| `TF-VAL-001B-005B` | `sensitivity_ready` | `TF-VAL-001B-SENS-005B-ALTSUAPE` | Run an explicit Suape alternate-port sensitivity if the runner can compute road access from forced `BRSUA` to Recife. | Use forced destination port `BRSUA` and `1844 nm` (`3415.088 km`) for BRRIG -> BRSUA from the documented reference. On-carriage is computed transparently by the runner from the forced port to the destination. | Alternate-port sensitivity only; must not be presented as Recife. |

## 4. Runnable Sensitivity Assumptions

### `TF-VAL-001B-SENS-002-REFDIST`

Original Batch 001B case: `TF-VAL-001B-002`

Original Batch 001 case: `TF-VAL-002`

OD pair: Sao Paulo, SP -> Manaus, AM

Port assumption: `Porto de Santos` -> `Porto de Manaus`

Distance assumption: `3300 nm`, converted with `1 nm = 1.852 km` to `6111.6 km`.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, which summarizes Costa et al. (2025), Appendix 6, as an ANTAQ-based distance matrix and records BRMAO -> BRSSZ as `3300 nm`.

What it can support: sensitivity to replacing the original `SeaMatrix haversine fallback` maritime distance.

What it cannot support: a fully validated Santos -> Manaus baseline or a final cost/emissions conclusion without boundary review.

### `TF-VAL-001B-SENS-003B-ALTPECEM`

Original Batch 001B case: `TF-VAL-001B-003B`

Original Batch 001 case: `TF-VAL-003`

OD pair: Manaus, AM -> Fortaleza, CE, with Pecem as an explicit alternate destination port.

Port assumption: `Porto de Manaus` -> `BRPEC` / Pecem. This is not `Porto de Fortaleza`.

Distance assumption: `1569 nm`, converted with `1 nm = 1.852 km` to `2905.788 km`.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, which summarizes Costa et al. (2025), Appendix 6, and records BRMAO -> BRPEC as `1569 nm`.

Road-access treatment: the runner uses the forced destination port to build the last-mile road leg from Pecem to the destination. This is transparent in the output through forced-port and on-carriage fields.

What it can support: alternate-port sensitivity for a Fortaleza-region interpretation.

What it cannot support: validation of the original Manaus -> Porto de Fortaleza selected-port case.

### `TF-VAL-001B-SENS-005B-ALTSUAPE`

Original Batch 001B case: `TF-VAL-001B-005B`

Original Batch 001 case: `TF-VAL-005`

OD pair: Porto Alegre, RS -> Recife, PE, with Suape as an explicit alternate destination port.

Port assumption: `Porto do Rio Grande` -> `BRSUA` / Suape. This is not `Porto do Recife`.

Distance assumption: `1844 nm`, converted with `1 nm = 1.852 km` to `3415.088 km`.

Source/provenance: `docs/validation/tf_validation_batch_001_external_references.md`, which summarizes Costa et al. (2025), Appendix 6, and records BRRIG -> BRSUA as `1844 nm`.

Road-access treatment: the runner uses the forced destination port to build the last-mile road leg from Suape to the destination. This is transparent in the output through forced-port and on-carriage fields.

What it can support: alternate-port sensitivity for a Pernambuco interpretation.

What it cannot support: validation of the original Rio Grande -> Porto do Recife selected-port case.

## 5. Blocked Rows

The following rows remain blocked and should stay as planned rows if included in a mixed output artifact:

- `TF-VAL-001B-003A`: blocked because exact Porto de Manaus -> Porto de Fortaleza maritime distance/source is missing.
- `TF-VAL-001B-004B`: blocked because a defensible alternate origin port and distance rule are missing.
- `TF-VAL-001B-005A`: blocked because exact Porto do Rio Grande -> Porto do Recife maritime distance/source is missing.

## 6. Thesis Boundary

Sensitivity outputs can show whether cost and emissions estimates change materially under documented distance and port assumptions. They cannot by themselves support robust thesis conclusions. Final classification must still use `docs/tf_result_classification_rules.md` and separate:

- validated baseline results;
- record-only and excluded cases;
- blocked cases;
- alternate-port sensitivity results;
- reference-distance sensitivity results.

Issue #17 should consolidate these rows without mixing alternate-port sensitivity outputs into original selected-port validation tables.
