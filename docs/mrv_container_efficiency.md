# MRV Container Efficiency Processing

## Purpose

This preprocessing step converts EU MRV "Publication of Information" workbooks into processed artifacts consumed by runtime model components.

Runtime code reads only processed files under:

- `data/processed/cabotage_data/`

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

- `data/processed/cabotage_data/container_ship_efficiency_classes.json`
- `data/processed/cabotage_data/container_ship_fuel_rate_sea_by_class.json`
- `data/processed/cabotage_data/container_ship_hoteling_rate_by_class.json`

## Column Normalization and Extraction

Canonical fields are matched across workbook variations:

- `ship_type`
- `fuel_per_nm` from fuel-per-distance (`kg / n mile`)
- `co2_per_nm` from CO2-per-distance (`kg CO2 / n mile`)
- `fuel_per_transport_work_dwt` from fuel-per-transport-work(dwt) (`g / dwt carried · n miles`) when populated
- `fuel_per_transport_work_mass` from fuel-per-transport-work(mass) (`g / m tonnes · n miles`) as fallback
- `transport_work_dwt`, `transport_work_mass`, `distance_travelled` when available (fallback path)
- `fuel_rate_sea_t_per_h` from `Fuel consumption per time spent at sea [m tonnes / hour]` when available

## Vessel Class Derivation (Technical Efficiency Removed)

The old approach estimated deadweight from `Technical efficiency` (EEDI/EIV-like field). That field is not a direct carried-load or ship-size variable for this purpose, and it can misclassify vessels.

The updated method uses MRV fields directly tied to carried work.

### Size proxy hierarchy (`size_proxy_t`)

1. Preferred (dwt-based intensity proxy):

`size_proxy_t ~= (fuel_per_nm_kg * 1000) / fuel_per_transport_work_dwt_g_per_tnm`

2. Fallback (if available):

`size_proxy_t ~= transport_work_dwt_tnm / distance_travelled_nm`

3. If dwt transport-work is missing/invalid, use mass transport-work intensity:

`size_proxy_t ~= (fuel_per_nm_kg * 1000) / fuel_per_transport_work_mass_g_per_tnm`

4. Fallback (if available):

`size_proxy_t ~= transport_work_mass_tnm / distance_travelled_nm`

`Technical efficiency` is not used for class derivation.

## Vessel Class Rules

Classification thresholds remain:

- `container_small`: size_proxy < 20,000
- `container_feeder`: 20,000 <= size_proxy < 40,000
- `container_large`: size_proxy >= 40,000

## Metric Derivation

- `fuel_per_km = fuel_per_nm / 1.852`
- Sea-rate (`t/h`) from direct MRV column, with fallback:
  - `fuel_rate_sea_t_per_h = total_fuel_consumption_t / time_at_sea_h`

## Filtering

Rows are restricted to:

- `Ship type == "Container ship"`

Rows are removed when:

- `fuel_per_nm <= 0` (or missing) for class efficiency outputs
- `size_proxy_t <= 0` (or missing)

## Robust Statistics and Outlier Handling

Outliers can make class-level means unstable (especially for `container_large` where extreme right tails exist). For each class and each metric distribution, statistics are now computed class-locally (not globally).

Metrics covered:

- `fuel_per_nm`
- `fuel_per_km`
- `co2_per_nm`
- `size_proxy_t`
- `fuel_rate_sea_t_per_h`
- `fuel_rate_hoteling_t_per_h`

Stored summary fields per distribution:

- `mean`
- `median`
- `trimmed_mean_1pct` (drop values below p1 and above p99)
- `winsorized_mean_1pct` (cap values at p1/p99)
- `p0`, `p10`, `p25`, `p50`, `p75`, `p90`, `p99`, `p99_5`, `p99_9`
- `min`, `max`, `count`

Default reporting should prioritize robust central/tail values:

- `median`
- `p10`
- `p90`

Means are retained for completeness and diagnostics.

## Sanity Checks Logged by Script

- Size proxy distribution (`min`, `median`, `p90`, `max`)
- Counts per class
- Source counts used to derive size proxy
- Fuel-per-nm monotonic check (`small <= feeder <= large`)
- Hoteling ratio consistency check (max relative error between expected and derived hoteling medians)
- Per-class mean vs median vs `trimmed_mean_1pct` printout for `fuel_per_nm`
- Warning when `|mean - median| / median > 50%`

## Reproducibility Notes

- Header matching is token-based and deterministic.
- Numeric parsing supports scientific notation and strips non-numeric markers (for example `Division by zero!`) before coercion.
- Output artifacts are deterministic for fixed MRV inputs and preprocessing arguments.

## Current Run Snapshot (2026-03-04, aux/main ratio = 0.25)

- Total MRV rows loaded: 53,880
- Container rows before cleaning: 7,973
- Removed by fuel filter: 176
- Removed by size proxy filter: 295
- Container rows used for class efficiency: 7,678
- Container rows used for sea-rate stats: 7,678

Fuel-per-nm (`kg/nm`) summary:

- `container_small`: n=3,172 | median=93.145 | mean=100.606 | trimmed_mean_1pct=99.054
- `container_feeder`: n=1,406 | median=168.780 | mean=171.877 | trimmed_mean_1pct=171.241
- `container_large`: n=3,100 | median=270.310 | mean=4400.382 | trimmed_mean_1pct=273.611

Observed warning:

- `container_large` mean is unstable (relative gap to median > 50%), confirming strong high-end outliers and motivating robust summaries.
