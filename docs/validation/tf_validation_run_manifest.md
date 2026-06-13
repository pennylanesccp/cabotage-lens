# TF Validation Run Manifest

This manifest defines the metadata required for each controlled validation execution of CabotageLens. It is an execution record template only; do not enter inferred values, calculated results, or reference comparisons unless they were produced or collected during a documented validation run.

Use one manifest entry per validation case and keep the completed manifest with the corresponding output artifact.

## Execution Metadata

| Field | Unit / format | Description |
| --- | --- | --- |
| `case_id` | text | Stable identifier matching the validation sample template. |
| `execution_date` | ISO 8601 date or datetime | Date, and time if available, when the validation execution was run. |
| `git_commit_sha` | full or short SHA | Repository commit used for the execution. |
| `script_or_app_entry_point` | path | Script, notebook, CLI, or Streamlit app entry point used, for example `app/app_streamlit.py`. |
| `command_or_input_payload` | command text or artifact path | Exact command, app inputs, JSON payload, or path to the saved payload used for the run. |
| `operator` | text | Person or process responsible for the execution, if recorded. |
| `output_file_path` | path | Path to generated output file, exported result, screenshot, or saved run artifact. |
| `notes` | text | Free-form notes on anomalies, manual interventions, or context needed for audit. |

## Origin, Destination, And Cargo

| Field | Unit / format | Description |
| --- | --- | --- |
| `origin` | city/state or full address | Origin input exactly as submitted. |
| `destination` | city/state or full address | Destination input exactly as submitted. |
| `resolved_origin_coordinates` | latitude, longitude | Coordinates resolved by the geocoding provider or cache. |
| `resolved_destination_coordinates` | latitude, longitude | Coordinates resolved by the geocoding provider or cache. |
| `cargo_mass_t` | tonnes | Cargo mass used for the validation run. |
| `teu` | TEU | Container-equivalent quantity used for the validation run. |
| `cargo_basis_notes` | text | Notes on whether the case is mass-based, TEU-based, or converted between both. |

## Route And Distance Outputs

| Field | Unit / format | Description |
| --- | --- | --- |
| `selected_origin_port` | port name/code | Port selected for the pre-carriage to maritime transfer. |
| `selected_destination_port` | port name/code | Port selected for the maritime to on-carriage transfer. |
| `road_only_distance_km` | km | Direct road-only model distance. |
| `pre_carriage_distance_km` | km | Road distance from origin to selected origin port. |
| `sea_distance_nm` | nautical miles | Maritime distance between selected ports. |
| `sea_distance_km` | km | Maritime distance converted to kilometres, if the model reports or uses it. |
| `on_carriage_distance_km` | km | Road distance from selected destination port to destination. |
| `maritime_distance_source` | text | Source flag such as matrix, observed/corridor value, API-derived value, haversine/coastline fallback, or other documented source. |
| `route_cache_status` | text | Cache behavior for each route/geocoding lookup, such as hit, miss, refreshed, or manually supplied. |
| `fallback_flags` | text/list | Any fallback used for geocoding, routing, maritime distance, vessel class, fuel price, emission factor, or cost input. |

## Model Inputs And Boundaries

| Field | Unit / format | Description |
| --- | --- | --- |
| `fuel_prices` | BRL/L, BRL/t, or configured unit | Fuel prices used by mode and fuel type. |
| `fuel_price_dates` | ISO 8601 date or source period | Date or reference period for each fuel price. |
| `emission_factors` | factor with unit | Emission factors used by fuel type or mode. Preserve units exactly, such as kg CO2e/L, kg CO2e/kg, or kg CO2e/t. |
| `emission_factor_sources` | citation/source text | Source or configuration location for each emission factor. |
| `cost_boundary` | text | Cost scope used in the run, for example fuel-only, energy plus port operations, or another documented boundary. |
| `emissions_boundary` | text | Emissions scope used in the run, for example tank-to-wheel only or another documented boundary. |
| `model_version_or_config` | text/path | Any relevant configuration file, parameter set, or model mode used for the run. |

## Reference Comparison Fields

These fields should be completed only after independent references are collected.

| Field | Unit / format | Description |
| --- | --- | --- |
| `reference_road_distance_km` | km | Independent road-distance reference under the closest comparable route boundary. |
| `reference_sea_distance_nm` | nautical miles | Independent port-to-port or corridor maritime-distance reference. |
| `reference_source` | citation/source text | Source used for the independent comparison. |
| `reference_boundary_notes` | text | Boundary differences, such as route provider, tolls, ferry inclusion, intermediate ports, service pattern, or full freight-rate scope. |
| `validation_status` | controlled text | Draft status such as not_run, reference_needed, pass, pass_with_limitation, fail_data_issue, fail_boundary_mismatch, fail_operational_plausibility, or sensitivity_required. |
| `main_issue` | text | Primary issue found during validation, if any. |
| `recommended_action` | text | Correction, limitation wording, exclusion, sensitivity analysis, or further reference collection needed. |

## Audit Requirements

- Record units with every numeric value.
- Preserve the distinction between model output, external reference, and reviewer interpretation.
- Mark every fallback explicitly before comparing results.
- Do not compare fuel-only costs directly against full freight rates without recording the boundary mismatch.
- Do not use fallback maritime distances to support strong thesis conclusions without sensitivity analysis or clear confidence downgrade.
- Keep completed manifests with the raw output artifacts so validation results can be reproduced from the same commit, inputs, and assumptions.
