# TF Validation Batch 001 Results

Execution date: 2026-06-13

Git commit SHA: `18fa72c5097943cc6cb12dace414c9d1a45a2576`

Batch source: `docs/validation/tf_validation_execution_notes.md`

CLI inspected before execution:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --help
```

Cargo assumption for all cases: `cargo_t = 14`, interpreted as a 1 TEU / 14 t benchmark case. The CLI commands used `--cargo 14`. The CLI help reports `--cargo` as cargo mass in tonnes and identifies the benchmark default as `1 TEU ~= 14 t`.

This document records controlled model execution output only. It does not add independent reference values, validation tolerances, or final pass/fail conclusions against external references. Because independent road and maritime references have not yet been collected, completed cases are classified as `reference_needed` unless a CLI/runtime failure is observed.

The CLI logged a masked database target at runtime. The connection string is not reproduced here.

## Summary

| Case ID | OD pair | CLI status | Model output captured | Main issue | Preliminary validation status | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001` | Sao Paulo (SP) -> Santos (SP) | completed | yes | Close-to-port edge case; selected origin and destination port are both Porto de Santos; maritime distance used SeaMatrix haversine fallback with 0.0 km sea. | `reference_needed` | Collect independent road reference and document why cabotage is operationally inappropriate for this local movement. |
| `TF-VAL-002` | Sao Paulo (SP) -> Manaus (AM) | completed | yes | Northern/Amazon case; maritime distance used SeaMatrix haversine fallback. | `reference_needed` | Collect independent road, maritime/corridor, and service-plausibility references before interpreting model advantage. |
| `TF-VAL-003` | Manaus (AM) -> Fortaleza (CE) | completed | yes | Northern/coastal case; maritime distance used SeaMatrix haversine fallback. | `reference_needed` | Collect independent maritime/corridor and port-service references, especially for Manaus routing assumptions. |
| `TF-VAL-004` | Brasilia (DF) -> Salvador (BA) | completed | yes | Inland-to-coastal case selected Porto de Angra dos Reis as origin port; route logic requires operational review. | `reference_needed` | Check nearest-port/service plausibility and collect independent road and maritime references. |
| `TF-VAL-005` | Porto Alegre (RS) -> Recife (PE) | completed | yes | Long coastal stress case; maritime distance used SeaMatrix haversine fallback. | `reference_needed` | Collect independent port-to-port/corridor distance and emissions/cost intensity references. |

## Commands Attempted

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --help
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Sao Paulo, SP" --destiny "Santos, SP" --cargo 14
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Sao Paulo, SP" --destiny "Manaus, AM" --cargo 14
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Manaus, AM" --destiny "Fortaleza, CE" --cargo 14
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Brasilia, DF" --destiny "Salvador, BA" --cargo 14
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Porto Alegre, RS" --destiny "Recife, PE" --cargo 14
```

## `TF-VAL-001`: Sao Paulo (SP) -> Santos (SP)

Command used:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Sao Paulo, SP" --destiny "Santos, SP" --cargo 14
```

Execution status: completed

Cargo assumption: `14.000t`; interpreted for validation notes as 1 TEU / 14 t benchmark case.

Resolved origin and destination if printed:

- Origin label printed: `Sao Paulo, SP`
- Destination label printed: `Santos, SP`
- Resolved coordinates: not reported by CLI output

Selected ports if printed:

- Origin port: `Porto de Santos`
- Destination port: `Porto de Santos`
- Nearest-port notes printed: origin nearest distance `59.601 km` via gate `Ponta da Praia`; destination nearest distance `7.124 km` via gate `Ponta da Praia`

Model outputs printed:

| Field | Captured value |
| --- | --- |
| Road-only distance | `77.2 km` |
| Pre-carriage distance | `86.174 km` |
| Maritime distance | `0.0 km sea` |
| On-carriage distance | `9.031 km` |
| Road emissions | `138.3 kg CO2e` |
| Multimodal emissions | `183.6 kg CO2e` |
| Road cost | `R$ 315.87` |
| Multimodal cost | `R$ 419.23` |
| Maritime distance source | `SeaMatrix haversine fallback`; `haversine_km=0.000`, `coastline_factor=1.000`, `adjusted_km=0.000` |

Fallback flags if printed:

- SeaMatrix haversine fallback for `Porto de Santos` -> `Porto de Santos`.
- Separate hoteling skipped because MRV transport-work intensity is available for vessel class `container_feeder`.

Cache/source notes if printed:

- Coordinates for `Sao Paulo, SP` and `Santos, SP` came from canonical location cache role `alias`.
- Road direct route was a cache miss and was cached from ORS: `distance_km=77.160`, `provider=ors`.
- First-mile route was a cache hit: `distance_km=86.174`, `provider=ors`.
- Last-mile route was a cache hit: `distance_km=9.031`, `provider=ors`.
- Geometry summary printed `direct_source=ors`, `first_mile_source=cache`, `last_mile_source=cache`.
- Diesel prices loaded `27 rows`; bunker price printed as `VLSFO`, `R$ 2572.34/mt`, date `2025-11-17`.
- Evaluation context printed `truck=semi_27t`, `vessel_class=container_feeder`, `diesel_mode=lookup`, `hoteling=False`, `port_ops=True`.
- Result saved to table `analysis_results`.

Other printed model context:

- Sea vessel class: `container_feeder (168.78 kg/nm)`.
- Sea allocation: `mode=teu_share`, `share=0.0003`, `old_dwt=0.0005`, `new_teu=0.0003`, `ratio=0.645`, `fuel_g_per_tnm=6.070`, `source=vessel_class_transport_work_intensity`, `mode=transport_work_intensity`.
- Sea fuel breakdown: `sailing=0.0 kg`, `hoteling=0.0 kg`, `port_ops=4.1 kg`.
- Port ops: `scenario=santos_diesel_heavy`, `moves/call=1.0`, `calls=2`, `cargo_teu=1`.
- CLI comparison label: `WORSE: -32.7% (R$ -103.37)`.

Observed errors or warnings: no command failure or warning line was printed. The same-port cabotage construction and 0.0 km sea leg are expected edge-case review items.

Preliminary validation status: `reference_needed`

## `TF-VAL-002`: Sao Paulo (SP) -> Manaus (AM)

Command used:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Sao Paulo, SP" --destiny "Manaus, AM" --cargo 14
```

Execution status: completed

Cargo assumption: `14.000t`; interpreted for validation notes as 1 TEU / 14 t benchmark case.

Resolved origin and destination if printed:

- Origin label printed: `Sao Paulo, SP`
- Destination label printed: `Manaus, AM`
- Resolved coordinates: not reported by CLI output

Selected ports if printed:

- Origin port: `Porto de Santos`
- Destination port: `Porto de Manaus`
- Nearest-port notes printed: origin nearest distance `59.601 km` via gate `Ponta da Praia`; destination nearest distance `4.462 km` via centroid

Model outputs printed:

| Field | Captured value |
| --- | --- |
| Road-only distance | `3870.0 km` |
| Pre-carriage distance | `86.174 km` |
| Maritime distance | `2744.7 km sea` |
| On-carriage distance | `6.763 km` |
| Road emissions | `6937.5 kg CO2e` |
| Multimodal emissions | `583.8 kg CO2e` |
| Road cost | `R$ 16,347.22` |
| Multimodal cost | `R$ 746.97` |
| Maritime distance source | `SeaMatrix haversine fallback`; `haversine_km=2744.683`, `coastline_factor=1.000`, `adjusted_km=2744.683` |

Fallback flags if printed:

- SeaMatrix haversine fallback for `Porto de Santos` -> `Porto de Manaus`.
- Separate hoteling skipped because MRV transport-work intensity is available for vessel class `container_feeder`.

Cache/source notes if printed:

- Coordinates for `Sao Paulo, SP` and `Manaus, AM` came from canonical location cache role `alias`.
- Road direct route was a cache hit: `distance_km=3870.006`, `provider=ors`.
- First-mile route was a cache hit: `distance_km=86.174`, `provider=ors`.
- Last-mile route was a cache hit: `distance_km=6.763`, `provider=ors`.
- Geometry summary printed `direct_source=cache`, `first_mile_source=cache`, `last_mile_source=cache`.
- Diesel prices loaded `27 rows`; bunker price printed as `VLSFO`, `R$ 2572.34/mt`, date `2025-11-17`.
- Evaluation context printed `truck=semi_27t`, `vessel_class=container_feeder`, `diesel_mode=lookup`, `hoteling=False`, `port_ops=True`.
- Result saved to table `analysis_results`.

Other printed model context:

- Sea vessel class: `container_feeder (168.78 kg/nm)`.
- Sea allocation: `mode=teu_share`, `share=0.0003`, `old_dwt=0.0005`, `new_teu=0.0003`, `ratio=0.645`, `fuel_g_per_tnm=6.070`, `source=vessel_class_transport_work_intensity`, `mode=transport_work_intensity`.
- Sea fuel breakdown: `sailing=125.9 kg`, `hoteling=0.0 kg`, `port_ops=4.1 kg`.
- Port ops: `scenario=santos_diesel_heavy`, `moves/call=1.0`, `calls=2`, `cargo_teu=1`.
- CLI comparison label: `BETTER: 95.4% (R$ 15,600.24)`.

Observed errors or warnings: no command failure or warning line was printed. The Amazon-region route and haversine maritime fallback require independent reference and operational review.

Preliminary validation status: `reference_needed`

## `TF-VAL-003`: Manaus (AM) -> Fortaleza (CE)

Command used:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Manaus, AM" --destiny "Fortaleza, CE" --cargo 14
```

Execution status: completed

Cargo assumption: `14.000t`; interpreted for validation notes as 1 TEU / 14 t benchmark case.

Resolved origin and destination if printed:

- Origin label printed: `Manaus, AM`
- Destination label printed: `Fortaleza, CE`
- Resolved coordinates: not reported by CLI output

Selected ports if printed:

- Origin port: `Porto de Manaus`
- Destination port: `Porto de Fortaleza`
- Nearest-port notes printed: origin nearest distance `4.462 km` via centroid; destination nearest distance `6.554 km` via centroid

Model outputs printed:

| Field | Captured value |
| --- | --- |
| Road-only distance | `5569.6 km` |
| Pre-carriage distance | `7.563 km` |
| Maritime distance | `2391.2 km sea` |
| On-carriage distance | `8.656 km` |
| Road emissions | `9984.3 kg CO2e` |
| Multimodal emissions | `394.2 kg CO2e` |
| Road cost | `R$ 22,986.28` |
| Multimodal cost | `R$ 378.91` |
| Maritime distance source | `SeaMatrix haversine fallback`; `haversine_km=2391.151`, `coastline_factor=1.000`, `adjusted_km=2391.151` |

Fallback flags if printed:

- SeaMatrix haversine fallback for `Porto de Manaus` -> `Porto de Fortaleza`.
- Separate hoteling skipped because MRV transport-work intensity is available for vessel class `container_feeder`.

Cache/source notes if printed:

- Coordinates for `Manaus, AM` and `Fortaleza, CE` came from canonical location cache role `alias`.
- Road direct route was a cache hit: `distance_km=5569.609`, `provider=ors`.
- First-mile route was a cache hit: `distance_km=7.563`, `provider=ors`.
- Last-mile route was a cache hit: `distance_km=8.656`, `provider=ors`.
- Geometry summary printed `direct_source=cache`, `first_mile_source=cache`, `last_mile_source=cache`.
- Diesel prices loaded `27 rows`; bunker price printed as `VLSFO`, `R$ 2572.34/mt`, date `2025-11-17`.
- Evaluation context printed `truck=semi_27t`, `vessel_class=container_feeder`, `diesel_mode=lookup`, `hoteling=False`, `port_ops=True`.
- Result saved to table `analysis_results`.

Other printed model context:

- Sea vessel class: `container_feeder (168.78 kg/nm)`.
- Sea allocation: `mode=teu_share`, `share=0.0003`, `old_dwt=0.0005`, `new_teu=0.0003`, `ratio=0.645`, `fuel_g_per_tnm=6.070`, `source=vessel_class_transport_work_intensity`, `mode=transport_work_intensity`.
- Sea fuel breakdown: `sailing=109.7 kg`, `hoteling=0.0 kg`, `port_ops=4.1 kg`.
- Port ops: `scenario=santos_diesel_heavy`, `moves/call=1.0`, `calls=2`, `cargo_teu=1`.
- CLI comparison label: `BETTER: 98.4% (R$ 22,607.36)`.

Observed errors or warnings: no command failure or warning line was printed. The Manaus-origin maritime route requires independent corridor/service review before interpretation.

Preliminary validation status: `reference_needed`

## `TF-VAL-004`: Brasilia (DF) -> Salvador (BA)

Command used:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Brasilia, DF" --destiny "Salvador, BA" --cargo 14
```

Execution status: completed

Cargo assumption: `14.000t`; interpreted for validation notes as 1 TEU / 14 t benchmark case.

Resolved origin and destination if printed:

- Origin label printed: `Brasilia, DF`
- Destination label printed: `Salvador, BA`
- Resolved coordinates: not reported by CLI output

Selected ports if printed:

- Origin port: `Porto de Angra dos Reis`
- Destination port: `Porto de Salvador`
- Nearest-port notes printed: origin nearest distance `884.961 km` via gate `Gate`; destination nearest distance `1.530 km` via gate `Gate`

Model outputs printed:

| Field | Captured value |
| --- | --- |
| Road-only distance | `1472.9 km` |
| Pre-carriage distance | `1369.936 km` |
| Maritime distance | `1273.3 km sea` |
| On-carriage distance | `5.060 km` |
| Road emissions | `2640.4 kg CO2e` |
| Multimodal emissions | `2665.3 kg CO2e` |
| Road cost | `R$ 5,935.87` |
| Multimodal cost | `R$ 5,720.70` |
| Maritime distance source | `SeaMatrix haversine fallback`; `haversine_km=1273.273`, `coastline_factor=1.000`, `adjusted_km=1273.273` |

Fallback flags if printed:

- SeaMatrix haversine fallback for `Porto de Angra dos Reis` -> `Porto de Salvador`.
- Separate hoteling skipped because MRV transport-work intensity is available for vessel class `container_feeder`.

Cache/source notes if printed:

- Coordinates for `Brasilia, DF` and `Salvador, BA` came from canonical location cache role `alias`.
- Road direct route was a cache miss and was cached from ORS: `distance_km=1472.885`, `provider=ors`.
- First-mile route was a cache miss and was cached from ORS: `distance_km=1369.936`, `provider=ors`.
- Last-mile route was a cache hit: `distance_km=5.060`, `provider=ors`.
- Geometry summary printed `direct_source=ors`, `first_mile_source=ors`, `last_mile_source=cache`.
- Diesel prices loaded `27 rows`; bunker price printed as `VLSFO`, `R$ 2572.34/mt`, date `2025-11-17`.
- Evaluation context printed `truck=semi_27t`, `vessel_class=container_feeder`, `diesel_mode=lookup`, `hoteling=False`, `port_ops=True`.
- Result saved to table `analysis_results`.

Other printed model context:

- Sea vessel class: `container_feeder (168.78 kg/nm)`.
- Sea allocation: `mode=teu_share`, `share=0.0003`, `old_dwt=0.0005`, `new_teu=0.0003`, `ratio=0.645`, `fuel_g_per_tnm=6.070`, `source=vessel_class_transport_work_intensity`, `mode=transport_work_intensity`.
- Sea fuel breakdown: `sailing=58.4 kg`, `hoteling=0.0 kg`, `port_ops=4.1 kg`.
- Port ops: `scenario=santos_diesel_heavy`, `moves/call=1.0`, `calls=2`, `cargo_teu=1`.
- CLI comparison label: `BETTER: 3.6% (R$ 215.17)`.

Observed errors or warnings: no command failure or warning line was printed. The selected origin port and long pre-carriage leg require route-logic and service-plausibility review before use in conclusions.

Preliminary validation status: `reference_needed`

## `TF-VAL-005`: Porto Alegre (RS) -> Recife (PE)

Command used:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py --origin "Porto Alegre, RS" --destiny "Recife, PE" --cargo 14
```

Execution status: completed

Cargo assumption: `14.000t`; interpreted for validation notes as 1 TEU / 14 t benchmark case.

Resolved origin and destination if printed:

- Origin label printed: `Porto Alegre, RS`
- Destination label printed: `Recife, PE`
- Resolved coordinates: not reported by CLI output

Selected ports if printed:

- Origin port: `Porto do Rio Grande`
- Destination port: `Porto do Recife`
- Nearest-port notes printed: origin nearest distance `246.162 km` via gate `Gate`; destination nearest distance `1.292 km` via centroid

Model outputs printed:

| Field | Captured value |
| --- | --- |
| Road-only distance | `3768.6 km` |
| Pre-carriage distance | `317.409 km` |
| Maritime distance | `3214.0 km sea` |
| On-carriage distance | `1.850 km` |
| Road emissions | `6755.7 kg CO2e` |
| Multimodal emissions | `1058.6 kg CO2e` |
| Road cost | `R$ 15,074.20` |
| Multimodal cost | `R$ 1,685.21` |
| Maritime distance source | `SeaMatrix haversine fallback`; `haversine_km=3213.975`, `coastline_factor=1.000`, `adjusted_km=3213.975` |

Fallback flags if printed:

- SeaMatrix haversine fallback for `Porto do Rio Grande` -> `Porto do Recife`.
- Separate hoteling skipped because MRV transport-work intensity is available for vessel class `container_feeder`.

Cache/source notes if printed:

- Coordinates for `Porto Alegre, RS` and `Recife, PE` came from canonical location cache role `alias`.
- Road direct route was a cache miss and was cached from ORS: `distance_km=3768.551`, `provider=ors`.
- First-mile route was a cache miss and was cached from ORS: `distance_km=317.409`, `provider=ors`.
- Last-mile route was a cache hit: `distance_km=1.850`, `provider=ors`.
- Geometry summary printed `direct_source=ors`, `first_mile_source=ors`, `last_mile_source=cache`.
- Diesel prices loaded `27 rows`; bunker price printed as `VLSFO`, `R$ 2572.34/mt`, date `2025-11-17`.
- Evaluation context printed `truck=semi_27t`, `vessel_class=container_feeder`, `diesel_mode=lookup`, `hoteling=False`, `port_ops=True`.
- Result saved to table `analysis_results`.

Other printed model context:

- Sea vessel class: `container_feeder (168.78 kg/nm)`.
- Sea allocation: `mode=teu_share`, `share=0.0003`, `old_dwt=0.0005`, `new_teu=0.0003`, `ratio=0.645`, `fuel_g_per_tnm=6.070`, `source=vessel_class_transport_work_intensity`, `mode=transport_work_intensity`.
- Sea fuel breakdown: `sailing=147.5 kg`, `hoteling=0.0 kg`, `port_ops=4.1 kg`.
- Port ops: `scenario=santos_diesel_heavy`, `moves/call=1.0`, `calls=2`, `cargo_teu=1`.
- CLI comparison label: `BETTER: 88.8% (R$ 13,388.99)`.

Observed errors or warnings: no command failure or warning line was printed. The long maritime corridor relies on haversine fallback and requires independent port-to-port or corridor-distance reference.

Preliminary validation status: `reference_needed`

## Batch-Level Observations

- All five commands completed and wrote results to `analysis_results`.
- Coordinates were not printed by the CLI output for any case.
- The CLI printed maritime distance in kilometres, not nautical miles. No nautical-mile conversion was added in this document.
- Every case used `container_feeder` and `vessel_class_transport_work_intensity` for maritime fuel/emissions allocation.
- Every case printed `port_ops=True` and port operations scenario `santos_diesel_heavy`.
- Every case printed `cargo_teu=1` in the port-operations line.
- Every case printed SeaMatrix haversine fallback for the maritime distance source. This is the main batch-level validation concern and should be addressed through independent maritime references before any thesis conclusion treats the maritime distances as validated.
- No external references were collected during this execution task.

## Recommended Next Action

Collect independent references for the five cases before changing any preliminary validation status:

- independent road distances for all road-only and access legs where practical;
- independent port-to-port or corridor maritime distances, especially for Manaus and long coastal cases;
- service-plausibility evidence for selected port pairs;
- comparable emissions and cost intensity ranges under the same model boundary.

After references are collected, update the validation sample CSV and assign each case a defended status such as `pass_with_limitation`, `fail_boundary_mismatch`, `fail_operational_plausibility`, or `sensitivity_required`.
