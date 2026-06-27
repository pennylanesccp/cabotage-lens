# Batch 001B Rerun Assumptions And Checklist

## 1. Purpose

This document records the current Batch 001B rerun assumptions, implemented hooks, partial hooks, and remaining blockers.

Batch 001B is a corrected or alternate validation layer beside the historical Batch 001 record. It must not silently replace `docs/validation/tf_validation_batch_001_results.md`, and it must not introduce undocumented maritime distances, costs, emissions factors, fuel prices, vessel parameters, or port choices.

Case-level readiness classes and the handoff into issue #16 are defined in `docs/validation/tf_validation_batch_001b_methodology_decisions.md`.

The current tracked Batch 001B artifacts are planned/record-only artifacts unless a future command explicitly runs with `--execute`.

## 2. Batch 001B Principles

- Do not use `SeaMatrix haversine fallback` alone for strong thesis conclusions about maritime distance, emissions, cost, or road-sea-road advantage.
- Do not silently substitute nearby ports. Pecem must remain an explicit alternate-port scenario for Fortaleza, and Suape must remain an explicit alternate-port scenario for Recife.
- Treat same-port cases as warning/exclusion cases, not as normal cabotage corridors.
- Preserve original Batch 001 distance/source values beside any Batch 001B candidate value.
- Preserve source, source type, unit, provenance, and notes for any maritime distance override or external reference.
- Keep cost and emissions boundaries explicit. A maritime-distance correction changes route-confidence interpretation; it does not by itself validate fuel factors, emissions factors, or cost formulas.
- Do not run model reruns until the case-specific evidence and methodology decision are explicit.

## 3. Current Hook Status

Audit date: 2026-06-27.

### Implemented Hooks

| Hook | Current implemented support | Evidence |
| --- | --- | --- |
| Validation-specific Batch 001B artifact path | `modules/validation/batch_001b.py` reads an explicit config, builds rows, and writes CSV/JSON artifacts without persisting to application tables. `scripts/run_validation_batch_001b.py` defaults to non-executing planned output unless `--execute` is supplied. | `modules/validation/batch_001b.py`; `scripts/run_validation_batch_001b.py` |
| Forced origin and destination ports | Per-case `port_overrides` can resolve ports by name, alias, or code and export forced-port and provenance fields. | `resolve_port(...)`; `forced_origin_port`; `forced_destination_port`; `origin_port_override_provenance`; `destination_port_override_provenance` |
| Maritime-distance override and unit conversion | Per-case `maritime_distance_override` supports `value`, `unit`, source, source type, provenance, notes, lower/upper bounds, scenario type, and bound role. Nautical miles are converted using `1 nm = 1.852 km`. | `normalize_maritime_override(...)`; `convert_maritime_distance(...)`; `apply_maritime_distance_override(...)` |
| Maritime distance provenance | Sea legs can carry structured `distance_provenance` with `distance_value`, `unit`, `distance_km`, `distance_nm`, `source`, `source_type`, `notes`, and optional bounds. Base provenance is retained when directional/corridor distance replaces the base SeaMatrix value; original provenance is retained when a validation override is applied. | `modules/multimodal/distance_provenance.py`; `modules/multimodal/builder.py`; `modules/validation/batch_001b.py` |
| Source type classification | Maritime distance source types are normalized to thesis-facing categories: `seamatrix`, `haversine_fallback`, `manual_override`, and `external_reference`. | `maritime_distance_source_type(...)` |
| Same-port and cabotage-inappropriate flags | Batch 001B rows can emit `same_port_flag` and `cabotage_inappropriate_flag`. The route-quality warning module also emits non-blocking warnings for same-port, missing/zero/small maritime legs, fallback maritime distance, and local cabotage access-distance dominance. | `build_exclusion_row(...)`; `build_route_quality_warnings(...)` |
| Provenance-preserving output schema | The Batch 001B CSV/JSON schema includes original source fields, normalized source types, override fields, source notes, unit, bounds, and output status. | `ALL_OUTPUT_FIELDS`; `docs/validation/tf_validation_batch_001b_output_template.csv` |
| UI boundary transparency | Result details now label emissions as operational `TTW CO2e`, label costs as estimates/proxies, and show maritime distance source/provenance in the assumptions detail table. | `app/main/details/breakdown.py`; `app/main/details/assumptions.py` |

### Partially Implemented Hooks

| Hook | Current partial state | Remaining limitation |
| --- | --- | --- |
| Executed Batch 001B reruns | The runner can execute `model_rerun` cases only when a case is configured for execution. The current Batch 001B config keeps cases as `record_only` or `planned`. | No current Batch 001B case is thesis-ready for execution without explicit methodology decisions. |
| Maritime distance bounds | Bounds are supported in the override schema and output fields. | Current Batch 001B planned config uses point reference candidates or null values; it does not yet define accepted low/base/high bound scenarios. |
| Same-port/local-cabotage warnings | The app and validation artifacts can flag same-port, zero-sea, small-sea, and fallback-distance cases. | These are interpretation warnings, not service-frequency checks or legal/commercial validation of a cabotage service. |
| External reference candidates | Existing docs support selected candidate distances for Santos/Manaus, Manaus/Pecem, and Rio Grande/Suape. | The docs still do not decide whether those values are replacement baselines, bounds, or named sensitivity cases for Batch 001B. |
| UI maritime-distance provenance | The assumptions detail table displays source and normalized source type when present in the evaluation result. | The top summary cards intentionally remain uncluttered, and validation-only override rows are not exposed through normal app controls. |

## 4. Remaining Evidence And Methodology Blockers

| Case | Current status | Blocker |
| --- | --- | --- |
| `TF-VAL-001B-001` | `record_only`; same-port warning/exclusion | No normal cabotage rerun should be performed. The row is a route-logic limitation case only. |
| `TF-VAL-001B-002` | `planned`; documented `3300 nm` Santos/Manaus candidate | Decide whether `3300 nm` is a replacement, bound, or named sensitivity scenario before any model execution. |
| `TF-VAL-001B-003A` | `planned`; exact selected-port case | Exact Porto de Manaus -> Porto de Fortaleza distance/source remains missing from existing evidence. |
| `TF-VAL-001B-003B` | `planned`; Pecem alternate-port candidate with `1569 nm` reference | Decide whether Pecem is acceptable as an alternate-port sensitivity and document road access/boundary implications for Fortaleza versus Pecem. |
| `TF-VAL-001B-004A` | `record_only`; original Angra dos Reis chain excluded | No normal rerun should use the original Angra dos Reis container chain for the 1 TEU / 14 t benchmark. |
| `TF-VAL-001B-004B` | `planned`; alternate origin port unresolved | Select and document a defensible alternate origin port and its maritime-distance source before execution. |
| `TF-VAL-001B-005A` | `planned`; exact selected-port case | Exact Porto do Rio Grande -> Porto do Recife distance/source remains missing from existing evidence. |
| `TF-VAL-001B-005B` | `planned`; Suape alternate-port candidate with `1844 nm` reference | Decide whether Suape is acceptable as an alternate-port sensitivity and document road access/boundary implications for Recife versus Suape. |

The following remain outside the current Batch 001B scope unless a future methodology task explicitly expands the model boundary:

- WTW/LCA emissions.
- Commercial freight rates, margins, tariffs, schedules, service frequency, reliability, inventory time, insurance, and demurrage.
- Full supernetwork routing or optimization.
- Terminal productivity validation beyond the currently documented port-ops model boundary.
- New emission factors, fuel factors, vessel parameters, or cost formulas.

## 5. Output Schema Expectations

Batch 001B planned and executed artifacts should use `ALL_OUTPUT_FIELDS` from `modules/validation/batch_001b.py`.

The schema must preserve:

- maritime distance in km and, when available, nautical miles;
- `maritime_distance_unit`;
- `maritime_distance_source`;
- normalized `maritime_distance_source_type`;
- `maritime_distance_notes`;
- optional `maritime_distance_lower_bound_km` and `maritime_distance_upper_bound_km`;
- original Batch 001 maritime distance and source;
- normalized `original_maritime_distance_source_type`;
- forced-port fields and override provenance;
- same-port and cabotage-inappropriate flags;
- validation status, sensitivity flag, execution mode, and output status.

`docs/validation/tf_validation_batch_001b_output_template.csv`, `docs/validation/tf_validation_batch_001b_output.csv`, and `docs/validation/tf_validation_batch_001b_output.json` should stay schema-aligned with `ALL_OUTPUT_FIELDS`.

## 6. Batch 001B Validation Checklist

Before changing any planned row to an executed rerun:

- [ ] Maritime distance provenance is recorded.
- [ ] SeaMatrix, fallback, manual override, and external reference sources are distinguished through normalized source types.
- [ ] Fallback maritime distances are not used for strong thesis conclusions without reference evidence or sensitivity treatment.
- [ ] Same-port or cabotage-inappropriate routes are flagged.
- [ ] TTW CO2e and cost-estimate boundaries are visible in UI/output documentation.
- [ ] Original Batch 001 values and source notes are preserved.
- [ ] Model reruns are not performed unless explicitly requested and the case is evidence-ready.
- [ ] Any forced port is explicitly labeled and has provenance.
- [ ] Any alternate-port scenario is not presented as the original selected-port case.
- [ ] WTW/LCA factors remain outside the current operational TTW boundary.
- [ ] Commercial freight rates, schedules, service frequency, reliability, terminal productivity, and supernetwork limitations remain outside the current scope unless separately modeled and documented.

## 7. Current Non-Executing Artifact Refresh

The current tracked Batch 001B planned artifacts are generated from:

```powershell
.\venv\Scripts\python.exe scripts\run_validation_batch_001b.py --config docs\validation\tf_validation_batch_001b_config.json
```

This command omits `--execute`, emits record-only and planned rows, and does not perform model reruns.
