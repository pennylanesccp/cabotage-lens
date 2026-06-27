# TF Validation Batch 002 - Road Emission Factor Reconciliation

## Purpose

This is a diagnostic-only, benchmark-alignment-only check for Batch 002. It does not replace the CabotageLens baseline road model, does not change any formula in the application, and does not overwrite the Batch 002 benchmark outputs.

The check asks one narrow question: if the cached Batch 002 road distances are kept fixed, how much of the workbook-vs-CabotageLens road-emissions gap is reduced by applying the road fuel and emissions assumption documented for the Gustavo/Costa paper/workbook benchmark family?

## Source Assumption

The paper-assumption trail is the tracked literature note `docs/literature_audit/paper_notes/brazilian-cabotage-competitiveness-supernetwork-2024.md`, which records:

- Road diesel fuel consumption for a 6-axle truck: `FDc = 0.28 L/km` from page 11, Table 1, source CETESB 2021.
- Road diesel fuel energy content: `FDe = 35.52 MJ/L` from page 10, section 4.3.
- Road diesel WTW emission factor: `FDf = 86.50 gCO2eq/MJ` from page 10, section 4.3, source EPE 2022.

Important boundary caveat: this is a WTW CO2e factor. CabotageLens' operational baseline road model should not be silently replaced by it. It is used here only as a diagnostic alignment factor against the external benchmark.

## Formula

The diagnostic road factor is:

```text
diagnostic_kgCO2e_per_km = FDc * FDe * FDf / 1000
diagnostic_kgCO2e_per_km = 0.28 L/km * 35.52 MJ/L * 86.5 gCO2e/MJ / 1000
diagnostic_kgCO2e_per_km = 0.8602944 kgCO2e/km
```

For each row:

```text
diagnostic road kg CO2e/container = cached Batch 002 road_distance_km * 0.8602944
diagnostic road percent difference = (diagnostic road kg CO2e/container - workbook road kg CO2e/container) / workbook road kg CO2e/container * 100
```

The road distances are the distances already produced by the Supabase/cache-enabled Batch 002 rerun in `data/processed/cabotage_data/gustavo_excel_benchmark_summary.json`.

## Summary

| Metric | CabotageLens baseline road | Diagnostic road factor |
| --- | ---: | ---: |
| Mean absolute road percent difference | 199.8% | 43.9% |
| Median absolute road percent difference | 149.3% | 19.6% |

The previous cached Batch 002 baseline mean/median road percent difference is therefore 199.8%/149.3%. The diagnostic mean/median road percent difference is 43.9%/19.6%.

The diagnostic factor materially reduces the road-emissions gap for every row. This means road fuel-consumption and road-emission-factor assumptions explain a large share of the road-only mismatch.

However, the diagnostic factor does not fully eliminate the gap. Several rows remain materially above the workbook road values, especially Manaus/Fortaleza/Recife long corridors. Because the diagnostic reused CabotageLens cached road distances, remaining differences can still come from road-distance basis, route construction, per-container allocation, WTW/TTW boundary differences, or workbook-specific assumptions that are not fully reconciled here.

## Per-Row Reconciliation

| pair ID | origin | destination | cached road distance km | workbook road kg CO2e/container | CabotageLens baseline road kg CO2e/container | diagnostic road kg CO2e/container | baseline road percent difference | diagnostic road percent difference | diagnostic factor materially reduces gap | interpretation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `B002-01` | Manaus | Fortaleza | 5,569.6 | 1,733.9 | 9,984.3 | 4,791.5 | 475.8% | 176.3% | yes | large reduction; residual gap remains |
| `B002-02` | Manaus | Recife | 5,558.6 | 2,113.1 | 9,964.6 | 4,782.0 | 371.6% | 126.3% | yes | large reduction; residual gap remains |
| `B002-03` | Manaus | Rio de Janeiro | 4,280.7 | 2,902.2 | 7,673.7 | 3,682.6 | 164.4% | 26.9% | yes | large reduction; residual gap remains |
| `B002-04` | Manaus | Sao Paulo | 3,878.8 | 2,744.4 | 6,953.3 | 3,336.9 | 153.4% | 21.6% | yes | large reduction; residual gap small to moderate |
| `B002-05` | Fortaleza | Manaus | 5,564.2 | 1,982.3 | 9,974.6 | 4,786.8 | 403.2% | 141.5% | yes | large reduction; residual gap remains |
| `B002-06` | Fortaleza | Rio de Janeiro | 2,697.1 | 1,886.6 | 4,835.0 | 2,320.3 | 156.3% | 23.0% | yes | large reduction; residual gap small to moderate |
| `B002-07` | Fortaleza | Sao Paulo | 3,134.6 | 2,254.2 | 5,619.2 | 2,696.7 | 149.3% | 19.6% | yes | large reduction; residual gap small to moderate |
| `B002-08` | Recife | Manaus | 5,549.8 | 2,361.5 | 9,948.9 | 4,774.5 | 321.3% | 102.2% | yes | large reduction; residual gap remains |
| `B002-09` | Recife | Rio de Janeiro | 2,310.3 | 1,695.2 | 4,141.6 | 1,987.6 | 144.3% | 17.2% | yes | large reduction; residual gap small to moderate |
| `B002-10` | Recife | Sao Paulo | 2,643.0 | 1,934.8 | 4,738.0 | 2,273.8 | 144.9% | 17.5% | yes | large reduction; residual gap small to moderate |
| `B002-11` | Salvador | Manaus | 4,873.0 | 2,381.3 | 8,735.5 | 4,192.2 | 266.8% | 76.0% | yes | large reduction; residual gap remains |
| `B002-12` | Salvador | Fortaleza | 1,189.9 | 864.4 | 2,133.1 | 1,023.7 | 146.8% | 18.4% | yes | large reduction; residual gap small to moderate |
| `B002-13` | Salvador | Recife | 807.9 | 618.9 | 1,448.3 | 695.1 | 134.0% | 12.3% | yes | large reduction; residual gap small to moderate |
| `B002-14` | Rio de Janeiro | Manaus | 4,269.3 | 3,150.7 | 7,653.4 | 3,672.9 | 142.9% | 16.6% | yes | large reduction; residual gap small to moderate |
| `B002-15` | Rio de Janeiro | Fortaleza | 2,692.5 | 1,886.6 | 4,826.7 | 2,316.4 | 155.8% | 22.8% | yes | large reduction; residual gap small to moderate |
| `B002-16` | Rio de Janeiro | Recife | 2,309.3 | 1,695.2 | 4,139.8 | 1,986.7 | 144.2% | 17.2% | yes | large reduction; residual gap small to moderate |
| `B002-17` | Rio de Janeiro | Salvador | 1,630.7 | 1,193.2 | 2,923.3 | 1,402.9 | 145.0% | 17.6% | yes | large reduction; residual gap small to moderate |
| `B002-18` | Sao Paulo | Manaus | 3,870.0 | 2,992.8 | 6,937.5 | 3,329.3 | 131.8% | 11.2% | yes | large reduction; residual gap small to moderate |
| `B002-19` | Sao Paulo | Fortaleza | 3,133.9 | 2,254.2 | 5,617.9 | 2,696.1 | 149.2% | 19.6% | yes | large reduction; residual gap small to moderate |
| `B002-20` | Sao Paulo | Recife | 2,647.0 | 1,934.8 | 4,745.1 | 2,277.2 | 145.2% | 17.7% | yes | large reduction; residual gap small to moderate |
| `B002-21` | Sao Paulo | Salvador | 1,968.4 | 1,409.5 | 3,528.6 | 1,693.4 | 150.3% | 20.1% | yes | large reduction; residual gap small to moderate |

## Interpretation

This diagnostic shows that the road-only gap is strongly sensitive to the road fuel-consumption and road-emission-factor boundary. The external benchmark's `0.8602944 kgCO2e/km` diagnostic factor is much lower than the effective per-kilometer result implied by the CabotageLens 1 TEU / 14 t baseline run, so applying it to the same cached road distances reduces the mean absolute road percent difference by about 156 percentage points and the median by about 130 percentage points.

The major road-emissions gap is therefore largely explained by road fuel/emission-factor assumptions, but not completely. The residual row-level gaps mean this should be described as a benchmark-alignment sensitivity, not a validation or recalibration. The remaining mismatch still requires careful discussion of road-distance basis, vehicle and loading assumptions, WTW versus TTW/operational boundary, and whether the workbook road values are allocated on exactly the same per-container basis as the CabotageLens run.
