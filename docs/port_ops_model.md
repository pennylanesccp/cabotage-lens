# Port Ops Model (Moves-Based)

## Objective

Model terminal-side operations for each voyage using a reproducible, reference-grounded method based on container moves.

This module estimates additional fuel, emissions, and cost from:

- quay handling (`sts_quay`)
- yard handling (`rtg_yard`)
- terminal horizontal transport (`terminal_truck`)

Runtime uses only processed artifact data from:

- `data/processed/cabotage_data/port_ops_params_santos.json`

## Source References Used (local-only, not tracked)

- `docs/references/core/Dados Relatorio 2.xlsx`
- `docs/references/support/rtg-crane-energy-usage-analysis-2017.pdf`
- `docs/references/support/hybrid-rtg-diesel-battery-energy-management-2021.pdf`
- `docs/references/core/ship-hoteling-loading-unloading-emissions-se-asia-2022.pdf`
- `docs/references/core/brazilian-cabotage-decarbonization-pathways-fuels-2024.pdf`

## Boundary note

Current runtime port-ops emissions use the same operational TTW CO2e fuel-factor pathway as the rest of the app. WTW or LCA values from the literature audit, including alternative-fuel values such as HVO, should be treated as references for future sensitivity or scenario work and should not be substituted into this model without an explicit boundary change and validation path.

Port-ops cost outputs are model cost estimates for the included equipment/activity boundary. They are not full terminal tariffs or commercial freight-rate components unless those missing cost categories are added separately.

## Method

### 1) Moves basis

Runtime defaults now scale moves to the user cargo:

- `cargo_teu_resolved = ceil(cargo_teu)` if `cargo_teu` is provided
- Else `cargo_teu_resolved = ceil(cargo_t / t_per_teu_default)`
- Default `port_moves_per_call = cargo_teu_resolved` (cargo-based mode)
- `quay_moves_total = port_calls * port_moves_per_call`

Alternative terminal-level mode is still available:

- `full_call_mode=true` uses scenario full-call defaults (`p10/median/p90`) when no explicit override is provided.

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
- `Cargo (TEU, optional)` in Cargo section
- `Tonnes per TEU default` (default `14`)
- `Full-call mode (terminal-level)` (default OFF)
- `Port moves per call override` (0 uses default logic)
- `Port ops scenario`
- Existing `Port calls per voyage`

Result panel and JSON include resolved TEU and move source for traceability.

### CLI

- `--include-port-ops` / `--no-include-port-ops`
- `--cargo-teu`
- `--t-per-teu-default`
- `--full-call-mode` / `--no-full-call-mode`
- `--port-moves-per-call`
- `--port-ops-scenario`

Available in:

- `scripts/compare_single.py`
- `scripts/compare_bulk.py`

## Limitations

- STS per-move energy was not explicitly parameterized because no direct local per-move value was found in the provided references; STS is currently an explicit zero placeholder.
- TEU conversion (`t_per_teu_default`) is a pragmatic assumption (default `14`) and should be replaced by route/customer commodity mix when available.
- Electricity emission/cost factors are placeholders (0.0) pending local grid/tariff values in the provided references.
- Reefer loads and non-handling terminal energy were not included.
- Reviewed hoteling/port-operation papers can inform future checks, but pending or WTW/LCA evidence should not replace the current TTW port-ops factors without a separate implementation plan.

## Future improvements (still reference-constrained)

- Add STS-specific factor when a defensible per-move value is available in the existing reference set.
- Add non-zero electricity factor in params if a local factor is available in the provided sources.
- Calibrate move defaults by terminal/route slices using the workbook matrix structure.
