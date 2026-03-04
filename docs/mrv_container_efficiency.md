# MRV Container Efficiency Processing

## Purpose

This preprocessing step converts EU MRV "Publication of Information" workbooks into processed artifacts used by runtime model components.

Runtime code reads only processed files under `data/processed`.

## Raw MRV Source Files

- `data/raw/cabotage_data/2021-v216-06022026-EU MRV Publication of information.xlsx`
- `data/raw/cabotage_data/2022-v241-06022026-EU MRV Publication of information.xlsx`
- `data/raw/cabotage_data/2023-v85-08022026-EU MRV Publication of information.xlsx`
- `data/raw/cabotage_data/2024-v184-03032026-EU MRV Publication of information.xlsx`

## Script

- `calcs/mrv_container_efficiency.py`

Run:

```powershell
python calcs/mrv_container_efficiency.py
```

Optional hoteling ratio switch:

```powershell
python calcs/mrv_container_efficiency.py --aux-main-ratio 0.27
```

## Produced Artifacts

- `data/processed/container_ship_efficiency_classes.json`
- `data/processed/container_ship_fuel_rate_sea_by_class.json`
- `data/processed/container_ship_hoteling_rate_by_class.json`

## Column Normalization and Extraction

Canonical fields are matched across workbook variations:

- `ship_type`
- `fuel_per_nm` from fuel-per-distance (`kg / n mile`)
- `co2_per_nm` from CO2-per-distance (`kg CO2 / n mile`)
- `deadweight`
- `fuel_rate_sea_t_per_h` from `Fuel consumption per time spent at sea [m tonnes / hour]` when available

### Deadweight handling

The provided MRV workbooks do not expose an explicit `Deadweight` column in these published sheets.
To keep the method MRV-derived, a deadweight proxy is computed when needed:

- `deadweight_t ~= (co2_per_nm * 1000) / technical_efficiency_g_per_t_nm`

`technical_efficiency_g_per_t_nm` is parsed from the MRV `Technical efficiency` text.

### Sea fuel-rate handling

The direct MRV sea-rate column is used when populated. If missing/empty, a deterministic MRV fallback is used:

- `fuel_rate_sea_t_per_h = total_fuel_consumption_t / time_at_sea_h`

## Filtering

Rows are restricted to:

- `Ship type == "Container ship"`

Rows are removed when:

- `fuel_per_nm <= 0` (or missing) for class efficiency outputs
- `deadweight <= 0` (or missing)

## Vessel Class Rules

Based on deadweight (t):

- `container_small`: deadweight < 20,000
- `container_feeder`: 20,000 <= deadweight < 40,000
- `container_large`: deadweight >= 40,000

## Metric Derivation

- `fuel_per_km = fuel_per_nm / 1.852`
- Class efficiency JSON stores full distribution stats (`mean`, `median`, `p10`, `p25`, `p75`, `p90`, `min`, `max`, `count`).
- Sea-rate JSON stores `median`, `p10`, `p90`, and `sample_size` for `fuel_rate_sea_t_per_h`.

## Current Run Snapshot

- Total MRV rows loaded: 53,880
- Container rows before cleaning: 7,973
- Removed by fuel filter: 176
- Removed by deadweight filter: 237
- Container rows used for class efficiency: 7,736
- Container rows used for sea-rate stats: 7,736

Deadweight source in kept efficiency rows:

- `derived_from_technical_efficiency`: 7,736

Sea fuel-rate source in kept rows:

- `derived_total_fuel_div_time`: 7,736

## Reproducibility Notes

- Header matching is token-based and deterministic.
- Numeric parsing strips non-numeric markers (for example `Division by zero!`) before coercion.
- Output artifacts are deterministic for a fixed set of MRV files and preprocessing arguments.
