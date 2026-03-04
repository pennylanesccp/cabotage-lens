# Port Ops Model (Moves-Based)

## Objective

Model terminal-side operations for each voyage using a reproducible, reference-grounded method based on container moves.

This module estimates additional fuel, emissions, and cost from:

- quay handling (`sts_quay`)
- yard handling (`rtg_yard`)
- terminal horizontal transport (`terminal_truck`)

Runtime uses only processed artifact data from:

- `data/processed/cabotage_data/port_ops_params_santos.json`

## Source References Used (repo-local only)

- `references/Dados Relatorio 2.xlsx`
- `references/rtg_crane_energy_usage_analysis_2017.pdf`
- `references/hybrid_rtg_diesel_battery_energy_management_2021.pdf`
- `references/ship_hoteling_loading_unloading_emissions_se_asia_2022.pdf`
- `references/brazilian_cabotage_decarbonization_pathways_fuels_2024.pdf`

## Method

### 1) Moves basis

- `quay_moves_total = port_calls * port_moves_per_call`
- If `port_moves_per_call` is omitted/zero, runtime uses scenario default median from the processed params file.

### 2) Equipment activity

For each equipment class `e`:

- `equipment_moves_total_e = quay_moves_total * moves_per_container_e`

### 3) Fuel and energy

For each equipment class `e`:

- `diesel_liters_e = equipment_moves_total_e * diesel_l_per_move_e`
- `fuel_kg_e = diesel_liters_e * diesel_density_kg_per_l`
- `electricity_kwh_e = equipment_moves_total_e * electricity_kwh_per_move_e`

### 4) Emissions and costs

- Diesel CO2e uses shared runtime logic via `modules.fuel.emissions.estimate_fuel_emissions(...)` with `fuel_type=diesel`.
- Electricity CO2e uses `electricity_kg_co2e_per_kwh` from params (currently 0.0 placeholder due missing local factor in provided references).
- Fuel cost uses route diesel price (`R$/L`) already used by road legs.
- Electricity cost uses `electricity_price_brl_per_kwh` from params (currently 0.0 placeholder).

## Santos Scenarios

The artifact defines two scenarios:

- `santos_diesel_heavy`
- `santos_partially_electrified`

Default runtime scenario: `santos_diesel_heavy`.

### Parameter snapshot (current generated artifact)

- Default `port_calls`: 2
- Default `port_moves_per_call`: p10=26.0, median=156.0, p90=510.6
- `diesel_density_kg_per_l`: 0.85

`Diesel-heavy` median equipment factors:

- `rtg_yard`: 4.0 moves/container, 0.3551 L/move
- `terminal_truck`: 2.0 moves/container, 0.4947 L/move
- `sts_quay`: 1.0 moves/container, 0.0 L/move (placeholder)

`Partially-electrified` median equipment factors:

- `rtg_yard`: 4.0 moves/container, 0.2317 L/move
- `terminal_truck`: 2.0 moves/container, 0.4947 L/move
- `sts_quay`: 1.0 moves/container, 0.0 L/move (placeholder)

The RTG diesel reduction proxy (relative to base RTG diesel factor) comes from the hybrid RTG reference range (about 27% to 40.6%).

## UI and CLI controls

### Streamlit

Advanced panel includes:

- `Include port ops` (default ON)
- `Port moves per call (0 uses scenario default)`
- `Port ops scenario`
- Existing `Port calls per voyage`

Result panel shows a dedicated port-ops breakdown (scenario, moves, calls, fuel, CO2e).

### CLI

- `--include-port-ops` / `--no-include-port-ops`
- `--port-moves-per-call`
- `--port-ops-scenario`

Available in:

- `scripts/compare_single.py`
- `scripts/compare_bulk.py`

## Limitations

- STS per-move energy was not explicitly parameterized because no direct local per-move value was found in the provided references; STS is currently an explicit zero placeholder.
- Electricity emission/cost factors are placeholders (0.0) pending local grid/tariff values in the provided references.
- Reefer loads and non-handling terminal energy were not included.

## Future improvements (still reference-constrained)

- Add STS-specific factor when a defensible per-move value is available in the existing reference set.
- Add non-zero electricity factor in params if a local factor is available in the provided sources.
- Calibrate move defaults by terminal/route slices using the workbook matrix structure.
