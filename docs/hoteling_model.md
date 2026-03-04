# Hoteling Fuel and Emissions Model

## Objective

Add a first-order at-berth (hoteling) fuel/emissions component for container vessel classes, using:

- MRV-derived vessel class sea fuel rates (`t/h`)
- EMEP/EEA 2023 Tier 3 auxiliary/main ratios and phase load factors

Runtime reads only processed artifacts.

## Inputs

### 1) MRV class sea fuel rate artifact

- `data/processed/container_ship_fuel_rate_sea_by_class.json`

Contains class-level distributions of:

- `fuel_rate_sea_t_per_h`

### 2) Hoteling class rate artifact

- `data/processed/container_ship_hoteling_rate_by_class.json`

Contains class-level distributions of:

- `fuel_rate_hoteling_t_per_h`
- `ratio_used`
- `aux_main_ratio`

## Reference values (EMEP/EEA Guidebook 2023)

The following values are implemented and cited from EMEP/EEA Guidebook 2023:

- Table 3-18 (container ships): auxiliary/main nominal power ratio
  - world fleet reference around `0.25`
  - Mediterranean fleet reference around `0.27`
- Table 3-20 (load factors by phase)
  - Cruise: `ME=80%`, `AE=30%`
  - Hotelling (except tankers): `AE=40%`; guidebook also lists some ME contribution, but this first-order berth model ignores ME.
- Table 3-19 (default hotelling time)
  - Container ships: `14 h` default per call

## Derivation

Let:

- `r = P_AE / P_ME` (aux/main nominal ratio)
- Cruise equivalent power fraction:
  - `frac_cruise = 0.80 + 0.30 * r`
- Hoteling equivalent power fraction (first-order, AE-only):
  - `frac_hot = 0.40 * r`

Then:

- `ratio = frac_hot / frac_cruise`
- `hoteling_rate_t_per_h = sea_rate_t_per_h * ratio`

With defaults:

- `r=0.25` -> `ratio ~= 0.1143`
- `r=0.27` -> `ratio ~= 0.1226`

So hoteling rate is expected to be roughly 11-12% of sea rate.

## Runtime formula in evaluator

For each route:

- `fuel_sea_sailing_kg = distance_nm * fuel_per_nm_selected`
- `hoteling_hours_total = hoteling_hours_per_call * port_calls`
- `fuel_hoteling_kg = hoteling_hours_total * fuel_rate_hoteling_t_per_h_selected * 1000`
- `fuel_sea_total_kg = fuel_sea_sailing_kg + fuel_hoteling_kg`

CO2 uses the same sea fuel emission factor already used in the project for marine fuel.

## Runtime controls

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

## Sanity checks

- Changing `--include-hoteling` (or Streamlit toggle) changes sea-leg fuel, CO2, and total multimodal results.
- Increasing hours or port calls increases sea-leg totals monotonically.
- Hoteling median rate should be approximately 11-12% of sea median rate for `r` in `[0.25, 0.27]`.
