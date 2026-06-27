# TF Validation Batch 002 - Gustavo/Costa Workbook Benchmark

## 1. Purpose and scope

Batch 002 compares CabotageLens against the local Gustavo/Costa Excel workbook as an external benchmark for the TF defense. The objective is not exact reproduction of the workbook or related paper. The objective is to identify which city-pair comparisons are directionally useful, where the model and workbook boundaries diverge, and what can be said conservatively in the thesis.

This artifact uses only local repository code and the local workbook. No web research was performed. The workbook remains local-only and must not be committed.

## 2. Execution metadata

| Item | Value |
| --- | --- |
| Batch date | 2026-06-27 |
| Repository | `pennylanesccp/cabotage-lens` |
| Branch | `main` |
| Git commit SHA at execution | `00b65847169c6c3a6395f76a48af0ee7f60fbdfc` |
| Workbook path used | `C:\Users\Cliente\Documents\workspaces\personal\cabotage-lens\docs\references\core\Dados Relatorio 2.xlsx` |
| Tracked workbook status | local-only; ignored by Git under `docs/references/` |
| Benchmark script | `scripts/benchmark_gustavo_excel.py` |
| Benchmark module | `modules/multimodal/gustavo_benchmark.py` |
| Output CSV | `data/processed/cabotage_data/gustavo_excel_benchmark.csv` |
| Output JSON | `data/processed/cabotage_data/gustavo_excel_benchmark_summary.json` |

The generated JSON stores the workbook path as the repository-relative path `docs/references/core/Dados Relatorio 2.xlsx` so the tracked artifact does not expose a workstation-specific path.

Exact model command:

```powershell
.\venv\Scripts\python.exe scripts\benchmark_gustavo_excel.py --workbook "docs\references\core\Dados Relatorio 2.xlsx" --cargo-t 14 --cargo-teu 1 --t-per-teu-default 14 --allocation-load-factor 0.8 --vessel-class container_feeder --include-hoteling --hoteling-hours-per-call 14 --port-calls 2 --include-port-ops --no-full-call-mode --port-ops-scenario santos_diesel_heavy --output-csv data\processed\cabotage_data\gustavo_excel_benchmark.csv --output-json data\processed\cabotage_data\gustavo_excel_benchmark_summary.json --pretty --log-level ERROR
```

## 3. Batch 002A - Workbook inventory

The workbook was parsed first without broad methodological interpretation. The controlled inventory parsed sheet names and dimensions, then used the existing parser logic for two matrices:

| Parsed field group | Workbook sheet | Header used by parser | Fields used |
| --- | --- | --- | --- |
| Road benchmark matrix | `Resumo Cenario Base` | `Origem / Destino` | origin city, destination city, road kg CO2e/container |
| Cabotage benchmark matrix | `Cabotagem Total Base` | `Cidade` | origin city, destination city, cabotage kg CO2e/container |
| Workbook totals | `Resumo Cenario Base`; `Cabotagem Total Base` | `Total Origem CO2e (kg)`; `Total Origem` | total road kg CO2e, total cabotage kg CO2e |
| Derived comparison field | computed from parsed matrix values | n/a | savings percentage = `1 - cabotage / road` |

The inventory saw 36 matrix cells across six normalized city labels: Manaus, Fortaleza, Recife, Salvador, Rio de Janeiro, and Sao Paulo. Of these, 21 were positive, non-diagonal OD rows supported by the current app city mapping and therefore passed to the benchmark run. Fifteen rows were skipped: six self-pairs and nine zero/non-positive road rows. No workbook values were invented.

Workbook aggregate totals from the parsed matrices:

| Metric | Value |
| --- | ---: |
| Workbook road emissions | 7,614,970.5 kg CO2e |
| Workbook cabotage emissions | 4,159,789.5 kg CO2e |
| Aggregate workbook reduction | 45.4% |
| Mean parsed pair-level workbook reduction | 46.7% |

## 4. Batch 002B - Model benchmark run

The existing benchmark path completed successfully for all 21 supported positive OD rows.

| Model setting | Value |
| --- | --- |
| Cargo basis | 1 TEU / 14 t |
| `t_per_teu_default` | 14 t/TEU |
| Vessel class | `container_feeder` |
| Allocation load factor | 0.8 |
| Hoteling requested | `true`, 14 h/call, 2 calls |
| Hoteling effective treatment | Separate hoteling skipped by evaluator where transport-work intensity is available |
| Port operations | included |
| Port-ops scenario | `santos_diesel_heavy` |
| Full-call mode | `false` |
| Road routing | cache-first route leg builder, with live provider fallback |
| Maritime distance and intensity | SeaMatrix distance and route KPI where available; vessel-class transport-work intensity otherwise |

Run summary from `data/processed/cabotage_data/gustavo_excel_benchmark_summary.json`:

| Metric | Value |
| --- | ---: |
| Rows total | 21 |
| Successful rows | 21 |
| Failed rows | 0 |
| Skipped model rows | 0 |
| Directional sea-matrix KPI rows | 2 |
| Mean absolute road percent difference | 201.0% |
| Median absolute road percent difference | 150.5% |
| Mean absolute cabotage/multimodal percent difference | 53.5% |
| Median absolute cabotage/multimodal percent difference | 52.9% |
| Mean workbook savings percentage | 46.7% |
| Mean model savings percentage | 89.1% |

Cache/provider limitation: the configured Supabase route cache could not be read or written in this local run because the configured tenant/user was rejected. The script continued with in-memory live road routing provider results. This makes the generated artifacts a valid execution record, but the road-distance side is not cache-stabilized for future reruns until the database configuration is fixed or equivalent route rows are available in Supabase.

Supabase/cache rerun note: after the Supabase project was reactivated, Batch 002 was rerun on `main` at `3a7307558cec1ce161bcc9aa5fc5ff4953514a23` with the same intended benchmark basis. The rerun completed all 21 positive OD pairs, route cache read worked, a rollbacked route-cache write probe worked, and the run log showed 63 road-route cache hits with zero cache misses, zero route-cache read/write failures, and zero live provider distance writes. The tracked CSV/JSON now reflect this cache-enabled rerun. The road mismatch remained materially similar (mean/median absolute road difference 199.8%/149.3%), the multimodal mismatch remained large (mean/median absolute multimodal difference 60.8%/63.7%), and mean model savings increased to 92.7%. See `docs/validation/tf_validation_batch_002_rerun_comparison.md` for the per-row comparison.

## 5. Batch 002C - Boundary and comparability classification

All 21 model-run rows are only `partially_comparable`. They share the same city-pair labels and per-container benchmark unit, but the workbook's detailed route/service, distance, allocation, and emissions-boundary assumptions were not fully reconstructed in this issue.

Observed classification pattern:

- All 21 positive rows show the same direction: workbook cabotage and CabotageLens multimodal emissions are both lower than road-only emissions.
- Twenty rows are classified as `same_direction_large_gap` because the direction agrees but the absolute road and/or multimodal magnitudes diverge materially.
- One row, Sao Paulo -> Salvador, is classified as `same_direction_order_of_magnitude` because the savings percentages are closest while still requiring boundary and allocation caveats.
- No row is classified as `opposite_direction` or `model_error`.
- Secondary limitations that remain relevant across the set are `boundary_mismatch`, `distance_source_mismatch`, `allocation_mismatch`, possible `port_selection_mismatch`, and `reference_needed`.

Rerun classification update: the cache-enabled rerun keeps the same directional agreement, but all 21 rows should now be treated as `same_direction_large_gap`. The previous Sao Paulo -> Salvador `same_direction_order_of_magnitude` classification is not retained because the rerun multimodal value moved substantially lower while the road value stayed stable.

Likely explanation families:

- Road distance mismatch: the model used current live road routing because Supabase route cache access failed; workbook road distance basis was not aligned in this issue.
- Maritime distance mismatch: only two rows used directional SeaMatrix route fuel KPIs; the remaining rows used vessel-class transport-work intensity and SeaMatrix distances without proven workbook route equivalence.
- Selected port mismatch: the model maps cities to nearest app ports, while the workbook matrix uses city labels and may embed different terminal/service assumptions.
- Workbook route/service assumption mismatch: the workbook's cabotage service structure was not fully reconstructed from the workbook in this issue.
- TTW/WTW/LCA and CO2/CO2e mismatch: CabotageLens reports operational TTW CO2e; the workbook is labelled CO2e in the parsed matrices, but the underlying boundary still needs explicit source reconciliation before strong claims.
- Per-container versus per-tonne allocation mismatch: the run uses 1 TEU / 14 t, `container_feeder`, and 0.8 allocation load factor; the workbook's per-container allocation basis was not fully audited.
- Port operations and hoteling treatment: CabotageLens includes port operations and requests hoteling, with separate hoteling skipped when transport-work intensity is already used; workbook treatment is not aligned row-by-row here.
- Cost boundary mismatch: cost was generated by the model script but is not interpreted here because the requested comparison is emissions-focused and model cost is not a full commercial freight rate.
- Missing evidence: exact workbook route distances, route services, port selections, and boundary equations remain reference needs.

## 6. Required result tables

### A. Workbook inventory table

| workbook origin | workbook destination | mapped app origin | mapped app destination | workbook road kg CO2e/container | workbook cabotage kg CO2e/container | workbook savings percentage | mapping status | comparability status | notes |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Manaus | Manaus | Manaus, AM | Manaus, AM | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |
| Manaus | Fortaleza | Manaus, AM | Fortaleza, CE | 1733.9 | 751.6 | 56.7 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Manaus | Recife | Manaus, AM | Recife, PE | 2113.1 | 960.2 | 54.6 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Manaus | Salvador | Manaus, AM | Salvador, BA | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Manaus | Rio de Janeiro | Manaus, AM | Rio de Janeiro, RJ | 2902.2 | 1705.8 | 41.2 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Manaus | Sao Paulo | Manaus, AM | São Paulo, SP | 2744.4 | 1639.4 | 40.3 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Fortaleza | Manaus | Fortaleza, CE | Manaus, AM | 1982.3 | 1019.5 | 48.6 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Fortaleza | Fortaleza | Fortaleza, CE | Fortaleza, CE | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |
| Fortaleza | Recife | Fortaleza, CE | Recife, PE | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Fortaleza | Salvador | Fortaleza, CE | Salvador, BA | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Fortaleza | Rio de Janeiro | Fortaleza, CE | Rio de Janeiro, RJ | 1886.6 | 1151.8 | 39.0 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Fortaleza | Sao Paulo | Fortaleza, CE | São Paulo, SP | 2254.2 | 1085.3 | 51.9 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Recife | Manaus | Recife, PE | Manaus, AM | 2361.5 | 1255.9 | 46.8 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Recife | Fortaleza | Recife, PE | Fortaleza, CE | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Recife | Recife | Recife, PE | Recife, PE | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |
| Recife | Salvador | Recife, PE | Salvador, BA | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Recife | Rio de Janeiro | Recife, PE | Rio de Janeiro, RJ | 1695.2 | 943.6 | 44.3 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Recife | Sao Paulo | Recife, PE | São Paulo, SP | 1934.8 | 877.1 | 54.7 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Salvador | Manaus | Salvador, BA | Manaus, AM | 2381.3 | 1387.7 | 41.7 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Salvador | Fortaleza | Salvador, BA | Fortaleza, CE | 864.4 | 567.3 | 34.4 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Salvador | Recife | Salvador, BA | Recife, PE | 618.9 | 334.5 | 45.9 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Salvador | Salvador | Salvador, BA | Salvador, BA | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |
| Salvador | Rio de Janeiro | Salvador, BA | Rio de Janeiro, RJ | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Salvador | Sao Paulo | Salvador, BA | São Paulo, SP | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Rio de Janeiro | Manaus | Rio de Janeiro, RJ | Manaus, AM | 3150.7 | 1863.5 | 40.9 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Rio de Janeiro | Fortaleza | Rio de Janeiro, RJ | Fortaleza, CE | 1886.6 | 1043.1 | 44.7 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Rio de Janeiro | Recife | Rio de Janeiro, RJ | Recife, PE | 1695.2 | 810.4 | 52.2 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Rio de Janeiro | Salvador | Rio de Janeiro, RJ | Salvador, BA | 1193.2 | 560.7 | 53.0 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Rio de Janeiro | Rio de Janeiro | Rio de Janeiro, RJ | Rio de Janeiro, RJ | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |
| Rio de Janeiro | Sao Paulo | Rio de Janeiro, RJ | São Paulo, SP | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Sao Paulo | Manaus | São Paulo, SP | Manaus, AM | 2992.8 | 1959.1 | 34.5 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Sao Paulo | Fortaleza | São Paulo, SP | Fortaleza, CE | 2254.2 | 1138.7 | 49.5 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Sao Paulo | Recife | São Paulo, SP | Recife, PE | 1934.8 | 905.9 | 53.2 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Sao Paulo | Salvador | São Paulo, SP | Salvador, BA | 1409.5 | 656.3 | 53.4 | supported | partially_comparable | parsed for model benchmark; boundary still only partially aligned |
| Sao Paulo | Rio de Janeiro | São Paulo, SP | Rio de Janeiro, RJ | 0.0 | 0.0 | n/a | supported | not_comparable | zero/non-positive road value in workbook; skipped by script |
| Sao Paulo | Sao Paulo | São Paulo, SP | São Paulo, SP | 0.0 | 0.0 | n/a | supported | not_comparable | self-pair in matrix; not a corridor benchmark |

### B. Model benchmark comparison table

| pair ID | origin | destination | workbook road kg CO2e/container | model road kg CO2e/container | road percent difference | workbook cabotage kg CO2e/container | model multimodal kg CO2e/container | cabotage/multimodal percent difference | workbook savings percentage | model savings percentage | directional agreement | benchmark classification | main explanation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| `B002-01` | Manaus | Fortaleza | 1733.9 | 9976.9 | 475.4% | 751.6 | 482.5 | -35.8% | 56.7% | 95.2% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-02` | Manaus | Recife | 2113.1 | 9957.4 | 371.2% | 960.2 | 581.1 | -39.5% | 54.6% | 94.2% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-03` | Manaus | Rio de Janeiro | 2902.2 | 7673.7 | 164.4% | 1705.8 | 876.8 | -48.6% | 41.2% | 88.6% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-04` | Manaus | Sao Paulo | 2744.4 | 6953.6 | 153.4% | 1639.4 | 1077.9 | -34.2% | 40.3% | 84.5% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-05` | Fortaleza | Manaus | 1982.3 | 9981.9 | 403.5% | 1019.5 | 480.2 | -52.9% | 48.6% | 95.2% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-06` | Fortaleza | Rio de Janeiro | 1886.6 | 4820.6 | 155.5% | 1151.8 | 440.7 | -61.7% | 39.0% | 90.9% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-07` | Fortaleza | Sao Paulo | 2254.2 | 5621.4 | 149.4% | 1085.3 | 641.9 | -40.9% | 51.9% | 88.6% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-08` | Recife | Manaus | 2361.5 | 9958.0 | 321.7% | 1255.9 | 580.6 | -53.8% | 46.8% | 94.2% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-09` | Recife | Rio de Janeiro | 1695.2 | 4129.0 | 143.6% | 943.6 | 317.4 | -66.4% | 44.3% | 92.3% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-10` | Recife | Sao Paulo | 1934.8 | 4743.8 | 145.2% | 877.1 | 518.7 | -40.9% | 54.7% | 89.1% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-11` | Salvador | Manaus | 2381.3 | 8743.1 | 267.2% | 1387.7 | 689.9 | -50.3% | 41.7% | 92.1% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-12` | Salvador | Fortaleza | 864.4 | 2377.6 | 175.1% | 567.3 | 256.3 | -54.8% | 34.4% | 89.2% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-13` | Salvador | Recife | 618.9 | 1448.6 | 134.1% | 334.5 | 133.0 | -60.2% | 45.9% | 90.8% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-14` | Rio de Janeiro | Manaus | 3150.7 | 7653.4 | 142.9% | 1863.5 | 875.1 | -53.0% | 40.9% | 88.6% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-15` | Rio de Janeiro | Fortaleza | 1886.6 | 4812.9 | 155.1% | 1043.1 | 441.3 | -57.7% | 44.7% | 90.8% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-16` | Rio de Janeiro | Recife | 1695.2 | 4126.2 | 143.4% | 810.4 | 316.1 | -61.0% | 52.2% | 92.3% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-17` | Rio de Janeiro | Salvador | 1193.2 | 2909.4 | 143.8% | 560.7 | 204.9 | -63.5% | 53.0% | 93.0% | yes: both lower than road | `same_direction_large_gap` | same direction with directional sea KPI, but road/cabotage magnitudes remain far apart |
| `B002-18` | Sao Paulo | Manaus | 2992.8 | 6937.6 | 131.8% | 1959.1 | 1079.8 | -44.9% | 34.5% | 84.4% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-19` | Sao Paulo | Fortaleza | 2254.2 | 5617.7 | 149.2% | 1138.7 | 646.2 | -43.2% | 49.5% | 88.5% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-20` | Sao Paulo | Recife | 1934.8 | 4747.8 | 145.4% | 905.9 | 521.0 | -42.5% | 53.2% | 89.0% | yes: both lower than road | `same_direction_large_gap` | same direction, but route distance source, workbook boundary, and per-container allocation are not aligned |
| `B002-21` | Sao Paulo | Salvador | 1409.5 | 3531.0 | 150.5% | 656.3 | 1432.2 | 118.2% | 53.4% | 59.4% | yes: both lower than road | `same_direction_order_of_magnitude` | closest savings alignment; still boundary/allocation mismatch and high directional sea intensity |

### C. Thesis interpretation table

| pair ID | final benchmark use category | allowed thesis use | prohibited thesis use | recommended wording |
| --- | --- | --- | --- | --- |
| `B002-01` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Manaus -> Fortaleza, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-02` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Manaus -> Recife, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-03` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Manaus -> Rio de Janeiro, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-04` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Manaus -> Sao Paulo, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-05` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Fortaleza -> Manaus, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-06` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Fortaleza -> Rio de Janeiro, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-07` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Fortaleza -> Sao Paulo, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-08` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Recife -> Manaus, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-09` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Recife -> Rio de Janeiro, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-10` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Recife -> Sao Paulo, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-11` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Salvador -> Manaus, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-12` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Salvador -> Fortaleza, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-13` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Salvador -> Recife, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-14` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Rio de Janeiro -> Manaus, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-15` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Rio de Janeiro -> Fortaleza, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-16` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Rio de Janeiro -> Recife, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-17` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Rio de Janeiro -> Salvador, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-18` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Sao Paulo -> Manaus, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-19` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Sao Paulo -> Fortaleza, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-20` | `benchmark_supports_direction` | Use only as evidence that both benchmark and model favor the cabotage/multimodal direction under their own boundaries. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Sao Paulo -> Recife, the comparison supports directional consistency only; magnitude differences require boundary and distance caveats. |
| `B002-21` | `benchmark_supports_order_of_magnitude` | Use as the strongest Batch 002 example of same-direction and rough savings-scale agreement. | Do not claim exact validation, calibrated replication, or commercial-rate/cost equivalence. | For Sao Paulo -> Salvador, the benchmark and model point in the same direction and the savings percentages are broadly aligned, but exact reproduction is not claimed. |

## 7. How to explain this benchmark to the TF committee

The Gustavo/Costa workbook is valuable because it is an external benchmark associated with the same broad research problem: Brazilian road freight versus cabotage-based alternatives. It is especially useful for the TF defense because it gives the committee a familiar comparator and forces CabotageLens to be checked against a non-self-generated reference.

The workbook should not be treated as absolute ground truth. This Batch 002 run did not fully reconstruct the workbook's internal distance sources, service assumptions, port choices, allocation logic, or emissions boundary. It also did not prove that CabotageLens reproduces the paper or the workbook. The correct explanation is narrower: when the same city labels and a 1 TEU / 14 t cargo basis are used, both the workbook and CabotageLens point in the same direction for all 21 positive OD pairs: the cabotage or multimodal alternative emits less than the road-only alternative.

The aligned part is therefore directional, not exact. The workbook's mean parsed pair-level reduction is 46.7%, while the first model run produced a much larger mean modeled reduction of 89.1% and the cache-enabled rerun produced 92.7%. That difference is too large to claim calibration or validation of magnitude. The safest committee wording is that Batch 002 supports the qualitative modal-shift direction but exposes boundary, route-assumption, and cargo-allocation gaps that must remain visible.

Several differences are expected:

- CabotageLens uses operational TTW CO2e. The workbook matrix is labelled CO2e, but its detailed TTW, WTW, LCA, and gas-boundary treatment was not fully audited here.
- CabotageLens uses current app port selection and SeaMatrix routing; the workbook may use different ports, service paths, or distance sources.
- CabotageLens uses a 1 TEU / 14 t benchmark with `container_feeder` and 0.8 allocation load factor; the workbook's per-container allocation logic still needs direct reconciliation.
- CabotageLens includes port operations and requests hoteling, with separate hoteling skipped when transport-work intensity is used; the workbook treatment may differ.
- CabotageLens cost outputs are model cost estimates and were not used here as commercial freight-rate validation.

Safe TF claims:

- The benchmark was parsed and run programmatically against the current model.
- All 21 positive workbook OD pairs supported by the app city mapping were executed successfully.
- The benchmark supports directional consistency: both the external workbook and CabotageLens favor the cabotage/multimodal direction for these rows.
- The comparison does not validate exact emissions magnitudes, exact ports, exact services, or exact cost boundaries.
- The large gaps are academically useful because they identify where boundary alignment, distance provenance, port selection, and allocation assumptions must be explained.

Claims that must not be made:

- Do not claim CabotageLens fully reproduces the Gustavo/Costa workbook or paper.
- Do not claim the workbook is absolute truth.
- Do not mix TTW, WTW, LCA, CO2, and CO2e boundaries.
- Do not claim model cost is a commercial freight rate.
- Do not treat city labels as proof of identical port/service assumptions.
- Do not use the larger CabotageLens savings percentages as validated headline conclusions.

## 8. Handoff to TF final report

Batch 002 should update the final TF writing, but the update should be conservative.

Recommended next edits:

- `docs/validation/tf_final_result_synthesis.md`: add Batch 002 as a new external-benchmark evidence layer. The synthesis should say Batch 002 supports direction but not calibrated magnitude.
- `docs/tf_final_report_draft.md`: update any broad Gustavo/Costa benchmark wording so it does not imply exact reproduction or strong order-of-magnitude validation for all pairs.
- Future section-by-section writing plan: add a specific Results/Discussion subsection for "External workbook benchmark" with the allowed claim: directionally aligned, boundary-limited, not ground truth.

This issue intentionally does not rewrite those files. The safest sequence is to review this Batch 002 artifact first, then make small TF-writing updates that cite it alongside Batch 001, Batch 001B, and the issue #16 sensitivity analysis.
