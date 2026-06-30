# Hoteling Fuel and Emissions Model

## Objective

Add a first-order at-berth (hoteling) fuel/emissions component for container vessel classes, using:

- MRV-derived vessel class sea fuel rates (`t/h`)
- EMEP/EEA 2023 Tier 3 auxiliary/main ratios and phase load factors

Runtime reads only processed artifacts.

## Inputs

### 1) MRV class sea fuel-rate artifact

- `data/processed/cabotage_data/container_ship_fuel_rate_sea_by_class.json`

Contains class-level distributions of:

- `fuel_rate_sea_t_per_h`

### 2) Hoteling class rate artifact

- `data/processed/cabotage_data/container_ship_hoteling_rate_by_class.json`

Contains class-level distributions of:

- `fuel_rate_hoteling_t_per_h`
- `ratio_used`
- `aux_main_ratio`

## References (EMEP/EEA Guidebook 2023)

- Table 3-18 (container ships): auxiliary/main nominal power ratio
  - world fleet: approximately `0.25`
  - Mediterranean fleet: approximately `0.27`
- Table 3-20 (load factors by phase)
  - Cruise: `ME=80%`, `AE=30%`
  - Hotelling (except tankers): `AE=40%` (first-order berth model ignores ME contribution)
- Table 3-19 (default hotelling time)
  - Container ships: `14 h` per call

## Derivation

Let:

- `r = P_AE / P_ME` (aux/main nominal ratio)
- Cruise equivalent power fraction:
  - `frac_cruise = 0.80 + 0.30 * r`
- Hoteling equivalent power fraction:
  - `frac_hot = 0.40 * r`

Then:

- `ratio = frac_hot / frac_cruise`
- `hoteling_rate_t_per_h = sea_rate_t_per_h * ratio`

Expected ratio values:

- `r=0.25` -> `ratio ~= 0.1143`
- `r=0.27` -> `ratio ~= 0.1226`

## Runtime Fuel and CO2 Formulas

For each route, sea/hoteling fuel is allocated to the user cargo (not charged as full-vessel fuel):

- Preferred sailing metric (MRV transport-work):
  - `fuel_sea_sailing_kg = (fuel_g_per_tnm * cargo_t * distance_nm) / 1000`
- Fallback sailing metric (if transport-work metric unavailable):
  - `ship_fuel_kg = distance_nm * fuel_per_nm_selected`
  - `cargo_share = min(cargo_t / size_proxy_t_median, 1.0)`
  - `fuel_sea_sailing_kg = ship_fuel_kg * cargo_share`
- Hoteling allocation:
  - `hoteling_hours_total = hoteling_hours_per_call * port_calls`
  - `hoteling_fuel_ship_kg = hoteling_hours_total * fuel_rate_hoteling_t_per_h_selected * 1000`
  - `fuel_hoteling_kg = hoteling_fuel_ship_kg * cargo_share`
- Marine subtotal:
  - `fuel_sea_total_kg = fuel_sea_sailing_kg + fuel_hoteling_kg`

CO2 uses the same marine fuel emission factor path already applied to sea fuel in the evaluator.

## Unit Consistency Audit

Current implementation keeps units consistent:

- `fuel_g_per_tnm` is `g/(t*nm)`
- `cargo_t` is `t` and `distance_nm` is `nm`
- `(fuel_g_per_tnm * cargo_t * distance_nm) / 1000` yields `kg`
- Fallback `fuel_per_nm_selected` remains `kg/nm` and is scaled by `cargo_share`
- `fuel_rate_hoteling_t_per_h_selected` is `t/h`
- `fuel_hoteling_kg` converts `t` to `kg` via `*1000`, then applies `cargo_share`
- `fuel_sea_total_kg` sums same-unit terms (`kg`)

Cost conversion uses `kg -> tonnes` before bunker price per tonne. CO2 uses marine EF per kg fuel.

## Runtime Controls

### Streamlit advanced panel

- `Include hoteling` (default ON)
- `Hoteling hours per port call` (default `14`)
- `Port calls per voyage` (default `2`)
- Derived display:
  - `hoteling_hours_total = hours_per_call * port_calls`

### CLI flags

- `--include-hoteling` / `--no-include-hoteling`
- `--hoteling-hours-per-call` (default `14`)
- `--port-calls` (default `2`)

Available in:

- `scripts/compare_single.py`
- `scripts/compare_bulk.py`

## Runtime Robustness Behavior

- Missing hoteling artifact raises a clear loader error indicating preprocessing must be run.
- Vessel class resolution uses fallback order:
  1. requested class
  2. `container_feeder`
  3. first valid class in payload
- Evaluator aligns hoteling class resolution with resolved sea class and logs if any mismatch occurs.
- Runtime output exposes hoteling provenance fields such as `hoteling_source_level`, `hoteling_basis`, `hoteling_warning`, and `hoteling_exclusion_reason`.
- When port-specific hotelling data are available in a future data path, they should be used directly. Missing port-specific values should not be interpreted as zero; they should follow the same transparent hierarchy used for port operations: observed value, weighted observed-port average, existing documented default, or explicit unavailable state.
- Separate hoteling remains skipped when the selected transport-work intensity already represents observed operational fuel, because adding it again would risk double counting.

## Provenance Interpretation

The source levels have the following interpretation:

- `observed`: observed port-specific data.
- `estimated_port_average`: weighted average intensity from observed peer ports.
- `literature_default`: documented model default from the current artifact/methodology.
- `unavailable`: no defensible observed or documented fallback value is available, so the component is explicitly marked rather than silently set to zero.

Estimated, documented-default, and unavailable states are lower-confidence than observed data and should be shown in thesis result tables or notes where they affect interpretation.

## Sanity Checks

Preprocessing logs:

- `ratio = (0.40*r) / (0.80 + 0.30*r)`
- class-level consistency between sea-rate median and hoteling-rate median scaling

Expected behavior:

- Enabling/disabling hoteling changes sea-leg fuel, CO2, and total multimodal result.
- Increasing hours-per-call or number of calls increases total sea fuel monotonically.
- Hoteling rate remains around 11-12% of sea rate for `r` in `[0.25, 0.27]`.

## Current Run Snapshot (2026-03-04, r=0.25)

- `ratio_used`: `0.1142857142857143`
- Class medians (`sea_rate_t/h -> hoteling_rate_t/h`):
  - `container_small`: `1.06298 -> 0.12148`
  - `container_feeder`: `2.33754 -> 0.26715`
  - `container_large`: `3.88190 -> 0.44365`
- Preprocessing sanity check result:
  - max relative error between `sea_median * ratio` and hoteling median: `0.0`
