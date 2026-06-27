# TF Validation Batch 002 - Supabase/Cache Rerun Comparison

## Purpose

This note compares the first Batch 002 Gustavo/Costa workbook benchmark run against the Supabase/cache-enabled rerun. The goal is not to force closer precision. The goal is to determine whether the large workbook-vs-model differences are mostly caused by cache/provider instability or by deeper methodology differences.

No web research was performed. The workbook remained local-only under `docs/references/core/Dados Relatorio 2.xlsx` and was not committed.

## Execution Metadata

| Item | Value |
| --- | --- |
| Repository | `pennylanesccp/cabotage-lens` |
| Branch | `main` |
| Rerun code SHA | `3a7307558cec1ce161bcc9aa5fc5ff4953514a23` |
| Previous tracked artifact source | pre-rerun `HEAD` at `3a7307558cec1ce161bcc9aa5fc5ff4953514a23`; initial execution metadata in the Batch 002 document records `00b65847169c6c3a6395f76a48af0ee7f60fbdfc` |
| Workbook path | `docs/references/core/Dados Relatorio 2.xlsx` |
| Output CSV | `data/processed/cabotage_data/gustavo_excel_benchmark.csv` |
| Output JSON | `data/processed/cabotage_data/gustavo_excel_benchmark_summary.json` |
| Rerun log inspected | `local/batch002_rerun_20260627.log` (ignored local file, not committed) |

Command used:

```powershell
.\venv\Scripts\python.exe scripts\benchmark_gustavo_excel.py --workbook "docs\references\core\Dados Relatorio 2.xlsx" --cargo-t 14 --cargo-teu 1 --t-per-teu-default 14 --allocation-load-factor 0.8 --vessel-class container_feeder --include-hoteling --hoteling-hours-per-call 14 --port-calls 2 --include-port-ops --no-full-call-mode --port-ops-scenario santos_diesel_heavy --output-csv data\processed\cabotage_data\gustavo_excel_benchmark.csv --output-json data\processed\cabotage_data\gustavo_excel_benchmark_summary.json --pretty --log-level INFO
```

## Supabase And Cache Status

| Check | Result |
| --- | --- |
| Supabase credentials/config available | yes; local Streamlit secrets were present and split Supabase Postgres settings loaded successfully |
| `SUPABASE_DB_URL` direct secret | not present |
| Split Supabase DB secrets | present |
| Supabase connection | succeeded |
| `route_cache_entries` table | existed before ensure step |
| Route cache total rows before rerun | 1,888 |
| Direct-road benchmark cache rows before rerun | 21 of 21 positive OD pairs |
| Route cache read | worked |
| Route cache write | rollbacked write probe succeeded before rerun |
| Auth/tenant/user errors | none observed in the probe or rerun log |
| Rerun road-distance source | cached road distances only |
| Rerun route-cache hits | 63 |
| Rerun route-cache misses | 0 |
| Rerun provider distance writes | 0 |
| Rerun route-cache read/write failures | 0 |

The rerun log showed cache hits for all road legs: 21 direct-road legs, 21 first-mile legs, and 21 last-mile legs. No live provider distance calculation was needed for the rerun.

## Run Summary

| Metric | Previous Batch 002 run | Supabase/cache rerun |
| --- | ---: | ---: |
| Rows parsed for model execution | 21 | 21 |
| Rows executed successfully | 21 | 21 |
| Rows failed | 0 | 0 |
| Rows skipped by model | 0 | 0 |
| Workbook inventory rows skipped before execution | 15 | 15 |
| Directional sea-matrix KPI rows | 2 | 0 |
| Mean absolute road percent difference | 201.0% | 199.8% |
| Median absolute road percent difference | 150.5% | 149.3% |
| Mean absolute cabotage/multimodal percent difference | 53.5% | 60.8% |
| Median absolute cabotage/multimodal percent difference | 52.9% | 63.7% |
| Mean workbook savings percentage | 46.7% | 46.7% |
| Mean model savings percentage | 89.1% | 92.7% |

The road-side result is effectively stable at aggregate level after switching from the first run's live/in-memory road distances to Supabase cached road distances. The multimodal side did not improve; the rerun reports zero directional sea-matrix KPI rows and all rows use `vessel_class_transport_work_intensity`, so remaining differences are not explained by road-route cache instability alone.

## Per-Row Delta Table

| pair ID | origin | destination | previous model road kg CO2e/container | new model road kg CO2e/container | road delta percentage | previous model multimodal kg CO2e/container | new model multimodal kg CO2e/container | multimodal delta percentage | previous classification | new classification | cache/provider note | interpretation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| `B002-01` | Manaus | Fortaleza | 9,976.9 | 9,984.3 | +0.1% | 482.5 | 394.2 | -18.3% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-02` | Manaus | Recife | 9,957.4 | 9,964.6 | +0.1% | 581.1 | 447.2 | -23.0% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-03` | Manaus | Rio de Janeiro | 7,673.7 | 7,673.7 | -0.0% | 876.8 | 449.7 | -48.7% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-04` | Manaus | Sao Paulo | 6,953.6 | 6,953.3 | -0.0% | 1,077.9 | 582.0 | -46.0% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-05` | Fortaleza | Manaus | 9,981.9 | 9,974.6 | -0.1% | 480.2 | 391.8 | -18.4% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-06` | Fortaleza | Rio de Janeiro | 4,820.6 | 4,835.0 | +0.3% | 440.7 | 354.4 | -19.6% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-07` | Fortaleza | Sao Paulo | 5,621.4 | 5,619.2 | -0.0% | 641.9 | 533.1 | -17.0% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-08` | Recife | Manaus | 9,958.0 | 9,948.9 | -0.1% | 580.6 | 446.7 | -23.1% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-09` | Recife | Rio de Janeiro | 4,129.0 | 4,141.6 | +0.3% | 317.4 | 297.2 | -6.4% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-10` | Recife | Sao Paulo | 4,743.8 | 4,738.0 | -0.1% | 518.7 | 484.9 | -6.5% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-11` | Salvador | Manaus | 8,743.1 | 8,735.5 | -0.1% | 689.9 | 416.1 | -39.7% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-12` | Salvador | Fortaleza | 2,377.6 | 2,133.1 | -10.3% | 256.3 | 187.8 | -26.7% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | cached road distance changed, but not enough to close the magnitude gap |
| `B002-13` | Salvador | Recife | 1,448.6 | 1,448.3 | -0.0% | 133.0 | 123.5 | -7.2% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-14` | Rio de Janeiro | Manaus | 7,653.4 | 7,653.4 | -0.0% | 875.1 | 447.9 | -48.8% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-15` | Rio de Janeiro | Fortaleza | 4,812.9 | 4,826.7 | +0.3% | 441.3 | 355.1 | -19.5% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-16` | Rio de Janeiro | Recife | 4,126.2 | 4,139.8 | +0.3% | 316.1 | 295.9 | -6.4% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-17` | Rio de Janeiro | Salvador | 2,909.4 | 2,923.3 | +0.5% | 204.9 | 203.7 | -0.6% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-18` | Sao Paulo | Manaus | 6,937.6 | 6,937.5 | -0.0% | 1,079.8 | 583.8 | -45.9% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal lower, so cache does not explain magnitude gap |
| `B002-19` | Sao Paulo | Fortaleza | 5,617.7 | 5,617.9 | +0.0% | 646.2 | 537.3 | -16.9% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | direction unchanged; remaining gap points to method boundaries |
| `B002-20` | Sao Paulo | Recife | 4,747.8 | 4,745.1 | -0.1% | 521.0 | 487.2 | -6.5% | `same_direction_large_gap` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road and multimodal stable; difference remains methodological |
| `B002-21` | Sao Paulo | Salvador | 3,531.0 | 3,528.6 | -0.1% | 1,432.2 | 393.5 | -72.5% | `same_direction_order_of_magnitude` | `same_direction_large_gap` | previous live/in-memory; rerun cache hit | road stable; multimodal much lower, removing the prior closest-match classification |

## Cargo And Allocation Comparability

CabotageLens was rerun as 1 TEU / 14 t with `t_per_teu_default = 14`, `allocation_load_factor = 0.8`, `vessel_class = container_feeder`, port operations included, hoteling requested, `hoteling_hours_per_call = 14`, `port_calls = 2`, `full_call_mode = false`, and `port_ops_scenario = santos_diesel_heavy`.

The workbook values parsed for comparison are reported as kg CO2e/container. The road matrix header is `Emissao Total de CO2e no Modal Rodoviario Direto por Conteiner (kg/conteiner)`, and the cabotage matrix header is `Emissao de CO2e por Conteiner na Cabotagem no Cenario Base (kg/conteiner)`. This means the comparison is aligned at the reported per-container level.

However, exact equivalence is not guaranteed until the workbook's internal payload mass, TEU definition, vehicle assumption, load factor, and allocation logic are extracted and reconciled. The readable workbook scan found container movement matrices in `Movimentacao de Conteineres` and a TEU table where 22G1 containers are counted as one TEU and 45G1/45R1 containers are counted as two TEU through formulas such as `K39=(K3+2*(K12+K21))`. The road and cabotage weekly-total matrices multiply per-container emissions by `Movimentacao de Conteineres` OD container counts. I did not find an explicit readable cell for payload mass, tonnes per container, truck load factor, `allocation_load_factor`, or a direct 14 t/container assumption.

Therefore, any remaining magnitude mismatch may still be explained by cargo/allocation boundary mismatch. The rerun improves confidence that the road-cache/provider issue is not the dominant explanation, but it does not prove that the workbook's internal cargo allocation is equivalent to the CabotageLens 1 TEU / 14 t benchmark.

## Defense-Oriented Interpretation

The cache-enabled rerun supports the same conservative TF defense interpretation as the first run, with stronger evidence against road-cache/provider instability as the main cause.

Allowed interpretation:

- The benchmark was rerun against the same reported per-container basis.
- All 21 positive supported workbook OD pairs executed successfully.
- All 21 rows remain directionally aligned: both the workbook and CabotageLens prefer cabotage/multimodal emissions over road-only emissions.
- The aggregate road mismatch changed only from 201.0% to 199.8% mean absolute difference and from 150.5% to 149.3% median absolute difference.
- The aggregate multimodal mismatch did not improve; it increased from 53.5% to 60.8% mean absolute difference and from 52.9% to 63.7% median absolute difference.
- Cache/provider instability was checked separately and is unlikely to be the only or primary cause of the large differences.

Remaining defensible explanation families:

- Same reported per-container basis, but not fully reconciled internal cargo/allocation logic.
- Possible road distance, fuel, or emission-factor mismatch.
- Possible selected-port, route, service, or SeaMatrix distance/KPI mismatch.
- Possible TTW/WTW/LCA or CO2/CO2e boundary mismatch.
- Possible port-ops and hoteling treatment mismatch.
- Cache/provider instability checked separately and not sufficient to explain the magnitude gaps.

The recommended TF defense wording is: Batch 002 supports directional consistency only. It does not validate calibrated emissions magnitudes, exact port/service choices, workbook allocation logic, or commercial freight-rate equivalence. After the Supabase/cache-enabled rerun, the large differences are more likely methodological than merely cache/provider instability.
