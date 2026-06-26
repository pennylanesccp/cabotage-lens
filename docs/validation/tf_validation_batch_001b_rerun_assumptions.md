# Batch 001B Rerun Assumptions And Required Hooks

## 1. Purpose

This document defines the assumptions and required code/data hooks for Batch 001B before any execution. It is a planning document only.

This document is not a results document. No Batch 001B reruns are performed here, no model outputs are changed, and no new maritime distances, costs, emissions factors, fuel prices, vessel parameters, or port choices are introduced. The original Batch 001 outputs in `docs/validation/tf_validation_batch_001_results.md` remain preserved as the raw execution record. Batch 001B should be treated as a corrected or alternate validation layer that sits beside Batch 001, not as a silent replacement for Batch 001.

The immediate purpose is to make the rerun assumptions explicit enough that a later execution issue can be reproducible, auditable, and defensible for thesis use.

## 2. Batch 001B principles

- Do not use `SeaMatrix haversine fallback` as the sole basis for strong thesis conclusions about maritime distance, emissions, cost, or road-sea-road advantage.
- Do not silently substitute nearby ports. Pecem must not be treated as Fortaleza unless the case is explicitly labeled as a Pecem alternate-port scenario. Suape must not be treated as Recife unless the case is explicitly labeled as a Suape alternate-port scenario.
- Alternate-port scenarios must be explicitly labeled and linked back to the original Batch 001 case.
- Same-port cases should be treated as cabotage-inappropriate, warning, or exclusion cases, not as normal cabotage corridors.
- Corrected or bounded maritime distances must preserve source, unit, provenance, and the rule used to apply them.
- Cost and emissions boundaries must remain explicit. A maritime-distance correction does not automatically validate cost or emissions unless the boundary assumptions remain compatible and visible.
- Preserve units and dimensional consistency. Maritime distance may be stored in kilometres for the model while thesis comparison may require nautical miles; any conversion must be explicit.
- Preserve original Batch 001 output values and fallback notes for comparison with Batch 001B.
- Do not upgrade validation status from Batch 001B execution alone unless the rerun output and independent evidence are both available.

## 3. Required hooks audit

Audit date: 2026-06-26.

Scope inspected: `scripts/compare_single.py`, `scripts/compare_bulk.py`, `modules/multimodal/builder.py`, `modules/multimodal/evaluator.py`, `modules/multimodal/persistence.py`, `modules/cabotage/sea_matrix.py`, `modules/infra/db/multimodal.py`, `modules/infra/db/bulk_runs.py`, `docs/validation/tf_validation_run_manifest.md`, and `docs/validation/tf_validation_sample_template.csv`. This was source inspection only; no model execution was performed.

| Hook | Needed for | Current support | Evidence in code/docs | Gap | Recommended action |
| --- | --- | --- | --- | --- | --- |
| Force origin port | `TF-VAL-001B-004B` and any alternate-origin scenario. | Partial internal support only. `build_path_geometry_from_resolved(...)` accepts `port_origin`, and tests exercise this path, but `compare_single.py` does not expose a CLI/config argument for it. | `modules/multimodal/builder.py` accepts `port_origin` and uses it instead of `find_nearest_port`; `scripts/compare_single.py` only accepts origin/destiny/cargo/model inputs and calls `build_path_geometry(...)` without a forced port. | No validation-facing way to force a port by name/code; no forced-port flag or provenance in result export. | Issue #14 should add minimal validation-rerun support, either a small config-driven rerun utility or CLI options that resolve a port from the tracked port catalog and record forced-port provenance. |
| Force destination port | `TF-VAL-001B-003B` for Pecem and `TF-VAL-001B-005B` for Suape, plus any exact-port rerun checks. | Partial internal support only. `build_path_geometry_from_resolved(...)` accepts `port_destiny`, but `compare_single.py` does not expose it. | Same builder path as origin port; Batch 001 docs require explicit Pecem and Suape handling. | No validation-facing destination-port override; no explicit alternate-port label in outputs. | Issue #14 should add destination-port forcing with an explicit alternate-port flag and source note. |
| Force or override maritime distance | `TF-VAL-001B-002` and any case where fallback maritime distance must be replaced by a documented corridor distance. | Not supported as a first-class validation hook. SeaMatrix can return matrix distance or haversine fallback, and enriched directional stats can replace the sea-leg distance when present, but there is no per-case CLI/config override. | `SeaMatrix.km_with_source(...)` returns `matrix` or `haversine`; `build_path_geometry_from_resolved(...)` can replace the distance with directional stats. | No clean way to inject a documented Batch 001B distance without changing data or patching geometry in custom code; no override flag/provenance exported. | Issue #14 should add a minimal maritime-distance override object with value, unit, source, provenance, and original fallback value preserved. |
| Represent maritime distance bounds or sensitivity values | `TF-VAL-001B-002`, and possibly `TF-VAL-001B-003A/003B` and `TF-VAL-001B-005A/005B` if exact distance remains uncertain. | Not directly supported. Multiple explicit reruns could be created manually, but no bound schema exists. | Existing validation manifest has `reference_sea_distance_nm`; runtime result schema has only one `sea_km` value. | No min/max or low/base/high distance fields; no sensitivity scenario linkage. | Issue #14 should support either explicit scenario rows such as `distance_low`, `distance_base`, `distance_high`, or separate case IDs with a shared `original_case_id` and `sensitivity_required` flag. |
| Mark same-port / cabotage-inappropriate case | `TF-VAL-001B-001`. | Not supported as an explicit runtime flag. Same selected port can be inferred when origin and destination port names match, and SeaMatrix returns `0.0` for identical labels, but no warning/exclusion field is emitted. | `SeaMatrix.get(...)` returns `0.0` when the resolved labels match; `tf_validation_plan.md` says very short/local cabotage should be flagged as inappropriate for thesis conclusions. | No `same_port_flag`, `cabotage_inappropriate_flag`, warning, or validation status emitted by the runtime path. | Issue #14 should add a pre-evaluation or post-geometry rule that flags same-port cases and can skip normal cabotage evaluation when the validation plan requires exclusion. |
| Export override provenance | All Batch 001B cases with forced ports, alternate ports, corrected distances, bounds, or exclusion labels. | Not sufficient. Geometry includes `sea_leg.source`, but evaluator/persistence do not preserve maritime distance source or override provenance in structured output. | `builder.py` creates `sea_leg` with `source`; `evaluator.py` consumes `sea_leg.distance_km` but does not export `maritime_distance_source`; `modules/multimodal/persistence.py` flattens only numeric sea and result fields. | Provenance would remain in logs or manual notes, not in thesis-ready exported rows. | Issue #14 should export original source, override source, provenance note, forced-port fields, and fallback flags in JSON/CSV or a validation results artifact. |
| Preserve Batch 001 and Batch 001B outputs side by side | All corrected/alternate validation layers. | Partial support. Bulk runs have `run_id` and `scenario_key`, but the single-run `analysis_results` table is keyed by `destiny_name`, so reruns can overwrite by destination. | `modules/infra/db/bulk_runs.py` defines run-scoped results; `modules/infra/db/multimodal.py` uses a unique index on `destiny_name` and updates on conflict. | Single-case validation outputs are not naturally versioned by `case_id`, `batch_id`, or `original_case_id`. | Issue #14 should avoid writing Batch 001B into the legacy single-result table unless table names are separated. Prefer a validation artifact or run-scoped table keyed by `batch_id` and `case_id`. |
| Export fields required for thesis tables | Final Batch 001B comparison tables and appendix traceability. | Partially supported by docs, not by runtime export. The validation manifest and sample CSV define many desired fields, but current runtime persistence lacks selected-port overrides, pre/on-carriage split in the flat single table, maritime source/provenance, and validation flags. | `docs/validation/tf_validation_run_manifest.md` and `docs/validation/tf_validation_sample_template.csv` include thesis-oriented fields; `flatten_evaluation_for_db(...)` exports only a narrower analytical payload. | Manual transcription would still be required and is error-prone. | Issue #14 should define a validation export schema before execution and write it directly from the rerun utility. |

Conservative conclusion: current code has enough internal building blocks to support selected-port injection in Python, but it does not yet provide a complete, auditable Batch 001B rerun interface. Maritime-distance override/bounds, same-port exclusion flags, override provenance, and thesis-table export are the controlling gaps.

## 4. Case-by-case Batch 001B assumptions

### `TF-VAL-001`: Sao Paulo (SP) -> Santos (SP)

Original case ID: `TF-VAL-001`.

Proposed Batch 001B case ID: `TF-VAL-001B-001`.

OD pair: Sao Paulo (SP) -> Santos (SP).

Current Batch 001 issue: The model selected `Porto de Santos` as both origin and destination port and recorded `0.0 km sea` using `SeaMatrix haversine fallback`. This is a same-port / close-to-port edge case, not a meaningful cabotage corridor.

Batch 001B assumption: Treat the case as a same-port warning/exclusion case. Do not perform a normal cabotage rerun unless code implements a same-port warning or cabotage-inappropriate behavior that must be verified.

Required hooks:

- `same_port_flag`;
- `cabotage_inappropriate_flag`;
- validation status or exclusion label that does not erase the original Batch 001 output;
- output note explaining that the case supports route-logic limitation only.

Required external evidence:

- Existing legal/methodological interpretation already documented in `docs/validation/tf_validation_batch_001_external_references.md`;
- optional independent road-distance note if the case remains in a quantitative appendix.

Rerun readiness: blocked for a normal rerun; partially ready for a warning/exclusion check after code adds the flag.

Whether code changes are likely needed: yes. Current code can produce the same-port geometry, but it does not emit a same-port or cabotage-inappropriate flag.

Expected output fields:

- `case_id`;
- `original_case_id`;
- `batch_id`;
- `origin`;
- `destination`;
- `selected_origin_port`;
- `selected_destination_port`;
- `same_port_flag`;
- `cabotage_inappropriate_flag`;
- `validation_status`;
- `notes`;
- original Batch 001 fallback fields preserved for comparison.

Thesis use if successful: Use only as a methodological edge case showing why same-port cabotage construction must be labeled, filtered, or excluded from road-sea-road advantage claims.

### `TF-VAL-002`: Sao Paulo (SP) -> Manaus (AM)

Original case ID: `TF-VAL-002`.

Proposed Batch 001B case ID: `TF-VAL-001B-002`.

OD pair: Sao Paulo (SP) -> Manaus (AM).

Current Batch 001 issue: The selected ports, `Porto de Santos` -> `Porto de Manaus`, are plausible, but the maritime distance came from `SeaMatrix haversine fallback`.

Batch 001B assumption: Keep `Porto de Santos` -> `Porto de Manaus`. Apply a corrected or bounded maritime-distance rule based on the ANTAQ/nautical-mile reference already documented in `docs/validation/tf_validation_batch_001_external_references.md`. Preserve the original fallback distance as a comparison value.

Required hooks:

- maritime-distance override or bounded sensitivity input;
- maritime-distance unit handling in km and, where available, nm;
- original fallback distance/source fields;
- corrected or bounded distance source/provenance fields;
- sensitivity flag if more than one distance value is used.

Required external evidence:

- The already documented ANTAQ-based nautical-mile corridor reference;
- a documented rule for whether that evidence is used as a single replacement, a lower/upper bound, or a sensitivity scenario;
- service-plausibility note for the Santos/Manaus corridor under the 1 TEU / 14 t benchmark.

Rerun readiness: partially ready. The port pair is defined, but execution is blocked until the distance application rule and code hook are explicit.

Whether code changes are likely needed: yes. Current runtime code does not expose a per-case maritime-distance override or bounds/provenance export.

Expected output fields:

- `case_id`;
- `original_case_id`;
- `batch_id`;
- `selected_origin_port`;
- `selected_destination_port`;
- `maritime_distance_km`;
- `maritime_distance_nm`, if available;
- `maritime_distance_override`;
- `maritime_distance_source`;
- `maritime_distance_provenance`;
- `fallback_flags`;
- road/multimodal distance, emissions, and cost fields;
- `sensitivity_required`;
- `validation_status`;
- `notes`.

Thesis use if successful: Potentially usable as a corrected sensitivity case for a plausible Santos/Manaus corridor, but only after showing whether cost and emissions conclusions survive the corrected or bounded maritime distance.

### `TF-VAL-003`: Manaus (AM) -> Fortaleza (CE)

Original case ID: `TF-VAL-003`.

Proposed Batch 001B case IDs:

- `TF-VAL-001B-003A`: Manaus -> Fortaleza, keeping `Porto de Fortaleza` only if exact evidence exists.
- `TF-VAL-001B-003B`: Manaus -> Pecem as an explicit alternate-port scenario, if evidence supports Pecem.

OD pair: Manaus (AM) -> Fortaleza (CE), with Pecem only as an explicit alternate-port interpretation.

Current Batch 001 issue: The model selected `Porto de Manaus` -> `Porto de Fortaleza`, while existing external evidence also points to Pecem as an important nearby comparator. Pecem must not be silently substituted for Fortaleza.

Batch 001B assumption:

- For `TF-VAL-001B-003A`, keep `Porto de Manaus` -> `Porto de Fortaleza` only if exact port-pair evidence is available.
- For `TF-VAL-001B-003B`, use `Porto de Manaus` -> Pecem only as an explicitly labeled alternate-port scenario.
- Document road access implications for Fortaleza versus Pecem.

Required hooks:

- forced destination port;
- alternate-port label;
- destination-port override provenance;
- maritime-distance override or exact evidence fields;
- road access fields for on-carriage changes.

Required external evidence:

- Exact service and maritime-distance evidence for `Porto de Manaus` -> `Porto de Fortaleza`, or a documented reason to use Pecem as an alternate;
- Pecem-specific evidence if `003B` is used;
- road access boundary note for Fortaleza versus Pecem.

Rerun readiness: blocked for `003A` until exact Fortaleza evidence or an explicit distance rule exists; partially ready for `003B` if Pecem evidence is accepted and a destination-port override hook is implemented.

Whether code changes are likely needed: yes. Current internal builder can accept a destination port in Python, but no CLI/config/provenance hook exists for a validation rerun.

Expected output fields:

- `case_id`;
- `original_case_id`;
- `batch_id`;
- `destination`;
- `selected_destination_port`;
- `forced_destination_port`;
- `destination_port_override`;
- `on_carriage_distance_km`;
- `maritime_distance_km`;
- `maritime_distance_nm`, if available;
- `maritime_distance_source`;
- `maritime_distance_provenance`;
- `fallback_flags`;
- emissions and cost fields;
- `validation_status`;
- `sensitivity_required`;
- `notes`.

Thesis use if successful: Use `003A` only if exact Fortaleza evidence supports it. Use `003B` only as a clearly labeled Pecem alternate-port scenario, not as a replacement for the original Fortaleza result.

### `TF-VAL-004`: Brasilia (DF) -> Salvador (BA)

Original case ID: `TF-VAL-004`.

Proposed Batch 001B case IDs:

- `TF-VAL-001B-004A`: original `Porto de Angra dos Reis` -> `Porto de Salvador` marked excluded/invalid.
- `TF-VAL-001B-004B`: Brasilia -> Salvador with a defensible alternate origin port, selected only with evidence.

OD pair: Brasilia (DF) -> Salvador (BA).

Current Batch 001 issue: The model selected `Porto de Angra dos Reis` as origin port, but that port is not defensible for the 1 TEU / 14 t container benchmark under the external evidence already documented.

Batch 001B assumption:

- Do not use Angra dos Reis for the 1 TEU / 14 t container benchmark.
- Mark the original Angra dos Reis chain as excluded or invalid for thesis-supporting conclusions.
- Select any alternate origin port only after evidence supports container/cabotage relevance and the road access boundary from Brasilia.

Required hooks:

- invalid-case or exclusion tracking;
- forced origin port for `004B`;
- origin-port override provenance;
- road access implication fields for the new first-mile leg;
- maritime-distance correction/bounds for the selected alternate origin port.

Required external evidence:

- Existing Angra dos Reis operational-plausibility evidence documented in `docs/validation/tf_validation_batch_001_external_references.md`;
- evidence for the selected alternate origin port before `004B` is executed;
- maritime-distance evidence for alternate origin port -> `Porto de Salvador`;
- road access boundary note from Brasilia to the alternate origin port.

Rerun readiness: `004A` is partially ready as an exclusion record after code supports invalid-case tracking. `004B` is blocked until a defensible alternate origin port and distance rule are selected.

Whether code changes are likely needed: yes. Same as forced origin-port hook, plus explicit invalid-case/exclusion export.

Expected output fields:

- `case_id`;
- `original_case_id`;
- `batch_id`;
- `selected_origin_port`;
- `forced_origin_port`;
- `origin_port_override`;
- `pre_carriage_distance_km`;
- `selected_destination_port`;
- `maritime_distance_km`;
- `maritime_distance_nm`, if available;
- `maritime_distance_source`;
- `maritime_distance_provenance`;
- `fallback_flags`;
- `validation_status`;
- `notes`;
- emissions and cost fields for `004B` only if a rerun is valid.

Thesis use if successful: Use `004A` as evidence of route-logic/operational-plausibility failure. Use `004B` only if the alternate origin port is explicitly defended and not presented as the original model-selected result.

### `TF-VAL-005`: Porto Alegre (RS) -> Recife (PE)

Original case ID: `TF-VAL-005`.

Proposed Batch 001B case IDs:

- `TF-VAL-001B-005A`: `Porto do Rio Grande` -> `Porto do Recife`, keeping Recife only if exact evidence exists.
- `TF-VAL-001B-005B`: `Porto do Rio Grande` -> Suape as an explicit alternate-port scenario, if evidence supports Suape.

OD pair: Porto Alegre (RS) -> Recife (PE), with Suape only as an explicit Pernambuco alternate-port interpretation.

Current Batch 001 issue: The model selected `Porto do Rio Grande` -> `Porto do Recife`, while existing evidence is stronger for Suape as a Pernambuco container/cabotage comparator. Suape must not be silently substituted for Recife.

Batch 001B assumption:

- For `TF-VAL-001B-005A`, keep `Porto do Recife` only if exact service and maritime-distance evidence exists.
- For `TF-VAL-001B-005B`, use Suape only as an explicitly labeled alternate-port scenario.
- Document road access implications for Recife versus Suape.

Required hooks:

- forced destination port for Suape;
- alternate-port label and destination-port override provenance;
- corrected or bounded maritime-distance fields;
- on-carriage distance fields for Recife versus Suape;
- fallback/source fields.

Required external evidence:

- Exact Rio Grande -> Recife service and maritime-distance evidence, or documented reason to use Suape as an alternate;
- Suape-specific evidence if `005B` is used;
- road access boundary note for Recife versus Suape.

Rerun readiness: blocked for `005A` until exact Recife evidence or a distance rule exists; partially ready for `005B` if Suape evidence is accepted and a destination-port override hook is implemented.

Whether code changes are likely needed: yes. Current internal destination-port injection is not exposed through a validation rerun interface and does not export provenance.

Expected output fields:

- `case_id`;
- `original_case_id`;
- `batch_id`;
- `origin`;
- `destination`;
- `selected_origin_port`;
- `selected_destination_port`;
- `forced_destination_port`;
- `destination_port_override`;
- `on_carriage_distance_km`;
- `maritime_distance_km`;
- `maritime_distance_nm`, if available;
- `maritime_distance_source`;
- `maritime_distance_provenance`;
- `fallback_flags`;
- emissions and cost fields;
- `validation_status`;
- `sensitivity_required`;
- `notes`.

Thesis use if successful: Use `005A` only if exact Recife evidence supports the model-selected port. Use `005B` only as a clearly labeled Suape alternate-port scenario with separate road access implications.

## 5. Expected Batch 001B output schema

Minimum fields to capture after future reruns:

| Field | Unit / format | Purpose |
| --- | --- | --- |
| `case_id` | text | Stable Batch 001B case identifier. |
| `original_case_id` | text | Link back to `TF-VAL-001` through `TF-VAL-005`. |
| `batch_id` | text | Use `Batch 001B` or another controlled batch label. |
| `origin` | text | Origin input exactly as submitted. |
| `destination` | text | Destination input exactly as submitted. |
| `cargo_t` | tonnes | Cargo mass; Batch 001 used 14 t. |
| `teu` | TEU | Container-equivalent quantity; Batch 001 used 1 TEU. |
| `road_only_distance_km` | km | Direct road-only model distance. |
| `pre_carriage_distance_km` | km | Origin to selected or forced origin port. |
| `maritime_distance_km` | km | Maritime distance used by the model for the rerun. |
| `maritime_distance_nm` | nautical miles | Reference or model maritime distance in nautical miles, if available. |
| `on_carriage_distance_km` | km | Selected or forced destination port to destination. |
| `selected_origin_port` | text | Port selected by model or resolved after override. |
| `selected_destination_port` | text | Port selected by model or resolved after override. |
| `forced_origin_port` | text/boolean-compatible | Forced origin port name/code, if any. |
| `forced_destination_port` | text/boolean-compatible | Forced destination port name/code, if any. |
| `origin_port_override` | boolean/text | Whether origin port differs from automatic selection and why. |
| `destination_port_override` | boolean/text | Whether destination port differs from automatic selection and why. |
| `maritime_distance_override` | boolean/text | Whether maritime distance was corrected, bounded, or manually supplied. |
| `maritime_distance_source` | text | Matrix, directional corridor, external reference, bounded assumption, fallback, or other controlled source label. |
| `maritime_distance_provenance` | citation/note | Source title, document path, access date if applicable, and rule used. |
| `same_port_flag` | boolean | True when selected/forced origin and destination ports are the same. |
| `cabotage_inappropriate_flag` | boolean | True when the case should not be treated as a normal cabotage corridor. |
| `fallback_flags` | text/list | Any geocoding, routing, maritime, fuel, vessel, or cost fallback used. |
| `road_emissions_kgco2e` | kg CO2e | Road-only emissions under the model boundary. |
| `multimodal_emissions_kgco2e` | kg CO2e | Multimodal emissions under the model boundary. |
| `road_cost_brl` | BRL | Road-only cost under the model boundary. |
| `multimodal_cost_brl` | BRL | Multimodal cost under the model boundary. |
| `validation_status` | controlled text | `not_run`, `excluded`, `reference_needed`, `pass_with_limitation`, `fail_boundary_mismatch`, `fail_operational_plausibility`, `sensitivity_required`, or another documented controlled label. |
| `sensitivity_required` | boolean | True when conclusions depend on uncertain distance, port, cost, or emissions assumptions. |
| `notes` | text | Short audit note preserving limitations and thesis-use boundary. |

If a bounded distance is used, the rerun artifact should also record the bound strategy. The preferred approach is to create separate explicit scenario rows rather than hiding multiple values in one field, for example one row per low/base/high distance assumption or one row per alternate port. Each row should have a stable `case_id`.

## 6. Recommended next issue

Issue #14 is required as an implementation issue unless the team decides Batch 001B will remain a manual documentation exercise only.

The current code does not yet support the required hooks as a complete, validation-facing workflow. It has partial internal support for forced ports through `build_path_geometry_from_resolved(...)`, and the bulk pipeline has run-scoped persistence, but the following Batch 001B requirements are not currently covered end to end:

- CLI/config-level forced origin and destination ports;
- per-case maritime-distance override or bounds;
- same-port and cabotage-inappropriate flags;
- invalid-case/exclusion records;
- override and fallback provenance in exported rows;
- side-by-side `case_id` / `original_case_id` / `batch_id` output;
- thesis-table fields exported without manual transcription.

Recommended issue #14 scope: implement the minimal support needed to run Batch 001B from an explicit validation configuration and export a thesis-ready artifact. The implementation should avoid broad app redesign, avoid data rewrites, and preserve the original Batch 001 outputs. A small validation-specific utility may be preferable to expanding the public Streamlit UI.

If issue #14 intentionally avoids code changes, then it should be scoped as documentation/config only and must clearly state that Batch 001B cannot yet be executed as an auditable model rerun without manual intervention.
