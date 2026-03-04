# MRV Container Efficiency Processing

## Purpose

This preprocessing step converts EU MRV "Publication of Information" workbooks into a single processed artifact with container vessel-class fuel intensity distributions.

Runtime code must read only:

- `data/processed/container_ship_efficiency_classes.json`

Raw MRV workbooks are used only during this one-time preprocessing step.

## MRV Source Files

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

## Column Normalization

The script normalizes headers and extracts these canonical fields (allowing name variants across workbook versions):

- `ship_type`
- `fuel_per_nm` from MRV fuel-per-distance column (`kg / n mile`)
- `co2_per_nm` from MRV CO2-per-distance column (`kg CO2 / n mile`)
- `deadweight`

### Deadweight handling

The provided workbooks do not contain an explicit `Deadweight` column in their published sheets.
To keep the method fully MRV-derived, the script computes a deadweight proxy when deadweight is missing:

- `deadweight_t ~= (co2_per_nm * 1000) / technical_efficiency_g_per_t_nm`

Where `technical_efficiency_g_per_t_nm` is parsed from the MRV `Technical efficiency` field (for example `EIV (29.43 gCO₂/t·nm)`).

No literature constants are hardcoded for this derivation.

## Filtering

Rows are restricted to:

- `Ship type == "Container ship"`

Rows are removed when:

- `fuel_per_nm <= 0` (or missing)
- `deadweight <= 0` (or missing)

## Metric Derivation

Primary metric from MRV:

- `fuel_per_nm` in `kg / n mile`

Converted metric:

- `fuel_per_km = fuel_per_nm / 1.852`

CO2 metric:

- `co2_per_nm` in `kg CO2 / n mile`

## Vessel Class Rules

Based on deadweight (t):

- `container_small`: deadweight < 20,000
- `container_feeder`: 20,000 <= deadweight < 40,000
- `container_large`: deadweight >= 40,000

## Aggregated Statistics

For each class and each metric (`fuel_per_nm`, `fuel_per_km`, `co2_per_nm`), the artifact stores:

- mean
- median
- p10
- p25
- p75
- p90
- min
- max
- count

Also stored:

- `sample_size`

## Current Output Snapshot

From the current run:

- Total MRV rows loaded: 53,880
- Container rows before cleaning: 7,973
- Removed by fuel filter: 176
- Removed by deadweight filter: 237
- Container rows after cleaning: 7,736
- Deadweight source in kept rows: 7,736 from `derived_from_technical_efficiency`

Class sizes and median fuel intensity:

- `container_small`: 2,318 rows, median `fuel_per_nm = 85.34`
- `container_feeder`: 1,991 rows, median `fuel_per_nm = 149.15`
- `container_large`: 3,427 rows, median `fuel_per_nm = 264.54`

## Reproducibility Notes

- Header normalization is deterministic and based on token matching.
- Numeric parsing removes non-numeric markers (for example `Division by zero!`) and coerces invalid values to null.
- The output JSON is deterministic for a fixed set of input workbooks.
