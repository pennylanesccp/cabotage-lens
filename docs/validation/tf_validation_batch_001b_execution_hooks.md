# Batch 001B Execution Hooks

## Purpose

Issue #14 added a validation-specific Batch 001B pathway for future corrected reruns. It does not change Streamlit behavior, does not change Batch 001 result files, and does not persist validation reruns into the legacy `analysis_results` table.

The implementation is centered on:

- `modules/validation/batch_001b.py` for config parsing, unit conversion, override handling, same-port/exclusion rows, and output writing;
- `scripts/run_validation_batch_001b.py` as the CLI wrapper;
- `docs/validation/tf_validation_batch_001b_config_template.json` as the starting config;
- `docs/validation/tf_validation_batch_001b_output_template.csv` as the output schema contract.

## Running Without Model Execution

The safe default is a non-executing export:

```powershell
.\venv\Scripts\python.exe .\scripts\run_validation_batch_001b.py --config docs\validation\tf_validation_batch_001b_config_template.json
```

Without `--execute`, `model_rerun` cases are emitted as planned rows and record-only cases are emitted as exclusion/warning rows. This mode is useful for reviewing assumptions and thesis-table completeness before any route calls.

## Running Future Reruns

To execute `model_rerun` cases after distances, ports, and provenance are complete:

```powershell
.\venv\Scripts\python.exe .\scripts\run_validation_batch_001b.py --config docs\validation\tf_validation_batch_001b_config_template.json --execute
```

Execution uses the existing multimodal builder/evaluator path but writes only CSV/JSON validation artifacts. It does not call `upsert_multimodal_result` and does not overwrite Batch 001 outputs.

## Forced Ports

Forced ports are represented per case:

```json
"port_overrides": {
  "destination": {
    "port": "BRPEC",
    "reason": "Explicit Pecem alternate-port scenario; not a silent replacement for Fortaleza.",
    "provenance": "docs/validation/tf_validation_batch_001_correction_plan.md"
  }
}
```

Supported lookup values include port names, aliases, and codes from `data/processed/cabotage_data/ports_br.json`. The resolver normalizes accents and repaired mojibake labels so codes such as `BRPEC` and `BRSUA` are stable choices.

The output records:

- automatic origin/destination port, when execution resolves them;
- forced origin/destination port;
- `origin_port_override` and `destination_port_override`;
- override provenance.

## Maritime-Distance Overrides

Maritime-distance overrides are represented per case:

```json
"maritime_distance_override": {
  "required": true,
  "value": null,
  "unit": "nm",
  "scenario_type": "bounded_or_corrected",
  "source_type": "external_reference",
  "source": "ANTAQ-based nautical-mile reference documented in tf_validation_batch_001_external_references.md",
  "provenance": "docs/validation/tf_validation_batch_001_external_references.md",
  "notes": "Optional short note explaining the distance treatment.",
  "lower_bound": null,
  "upper_bound": null,
  "bounds_unit": "nm"
}
```

When `value` is supplied, `unit` must be `km` or `nm`. Nautical miles are converted using `1 nm = 1.852 km`, and both kilometre and nautical-mile fields are exported. The original model/fallback maritime distance, source, and normalized source type are preserved in `original_maritime_distance_km`, `original_maritime_distance_source`, and `original_maritime_distance_source_type`.

`source_type` is optional but recommended. Supported thesis-facing categories are:

- `seamatrix`;
- `haversine_fallback`;
- `manual_override`;
- `external_reference`.

If `source_type` is omitted, the runner infers it conservatively from the source label and whether the value is an override. Optional `lower_bound` / `upper_bound` values can be supplied with `bounds_unit`, or as explicit `lower_bound_km`, `upper_bound_km`, `lower_bound_nm`, and `upper_bound_nm` fields.

Executed geometry also carries a nested `sea_leg.distance_provenance` object with `distance_value`, `unit`, `distance_km`, `distance_nm`, `source`, `source_type`, `notes`, and optional lower/upper bounds. When an override is applied, the original sea-leg provenance is retained as `sea_leg.original_distance_provenance`; when a SeaMatrix directional/corridor value replaces the base matrix/fallback value, the base provenance is retained as `sea_leg.base_distance_provenance`.

Bounded or sensitivity cases should be represented as separate explicit scenario rows with distinct `case_id` values and `scenario_type` / `bound_role` metadata.

## Same-Port And Invalid Cases

Record-only cases use `execution_mode: "record_only"` and can be emitted without numerical rerun. This supports:

- `TF-VAL-001B-001` as a same-port warning/exclusion case;
- `TF-VAL-001B-004A` as the Angra dos Reis invalid/excluded record.

The output records:

- `same_port_flag`;
- `cabotage_inappropriate_flag`;
- `validation_status` such as `warning_only` or `excluded`;
- notes linking the record back to the original Batch 001 case.

If a future `--execute` run resolves the same origin and destination port, the utility returns a warning-only row unless the case explicitly sets `allow_same_port_evaluation: true`.

## Output Artifacts

The default config writes:

- `docs/validation/tf_validation_batch_001b_output.csv`;
- `docs/validation/tf_validation_batch_001b_output.json`.

The output schema includes the minimum fields listed in `docs/validation/tf_validation_batch_001b_rerun_assumptions.md`, plus execution metadata fields for automatic ports and override provenance.

## Remaining For Issue #15

Before executing thesis-supporting Batch 001B reruns, issue #15 should complete the missing case assumptions:

- select and document any real maritime-distance replacement or bound;
- decide whether each exact selected port or alternate port is defensible;
- fill missing `value`, `source`, and `provenance` fields in the config;
- review planned output rows before running with `--execute`;
- run the corrected cases and review cost/emissions sensitivity under the documented boundaries.
