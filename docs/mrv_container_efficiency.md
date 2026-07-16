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

## Runtime Allocation Note

`fuel_per_nm` is a vessel-level intensity (`kg/nm`) and must not be charged entirely to small cargos.

The preferred runtime metric for cargo allocation is:

- `fuel_g_per_tnm` (`g/(t*nm)`) from MRV transport-work intensity

For a selected observed voyage corridor, runtime sailing fuel uses the
same-OD transport-work-weighted median and the sum of the selected path's
subleg distances:

- `fuel_kg_sailing = sum(pair_intensity_g_per_tnm * cargo_t * subleg_distance_nm) / 1000`

The offline corridor calculation separately derives voyage fuel for observed
activity by summing transport work over the actual sublegs for each ordered
origin/destination pair represented in a voyage:

- `observed_transport_work_tnm = sum(cargo_onboard_t * subleg_distance_nm)`
- `observed_fuel_kg = sum(intensity_g_per_tnm * cargo_onboard_t * subleg_distance_nm) / 1000`

For each ordered origin/destination pair, every resolved voyage observation
from every complete observed corridor contributes directly to the pair
estimator. It is not a median of corridor aggregates. With voyage intensity
`I_v` and full same-OD transport work `W_v`, the applied value is the lower
weighted median:

- `pair_intensity = min(x: sum(W_v for I_v <= x) >= 0.5 * sum(W_v))`

Only positive `W_v` values influence this weighted statistic. If all resolved
same-OD voyages have zero transport work, the system uses an explicitly labeled
ordinary median so the scenario does not turn a `0/0` diagnostic into missing
intensity. The rule uses no route-target value or manually chosen closeness
band.

Only complete corridors observed within one ANTAQ voyage are eligible. A
corridor is never synthesized by joining port-pair legs from different voyages.
Each voyage contributes once per ordered origin/destination pair. If repeated
calls create multiple eligible slices inside the same voyage, direct is
preferred and otherwise the shortest complete slice is retained, matching the
model's corridor criterion.
All observed alternatives are evaluated; the current rule prefers a usable
direct observed corridor and otherwise selects the complete corridor with the shortest
distance. That selection controls path and distance only. It does not restrict
the voyage population used by the same-OD pair intensity.

Terminal aliases in the ANTAQ tables are resolved to canonical port complexes.
Adjacent calls that resolve to the same canonical port are collapsed after
their net weight and TEU movements are summed, so no cargo movement is dropped.
For distinct ports, each subleg uses a positive sea-matrix distance when
available. Missing or nonpositive values use a coordinate-based haversine
fallback; `distance_source_counts` and each selected subleg retain that
provenance because the fallback is an approximation and can affect the
shortest-distance selection.

The normalized stop sequence is limited to ANTAQ calls represented in the
containerized-cargo pipeline; physical calls with no observed container
movement may be absent. If all derived transport work for a resolved subleg or
corridor is zero, the diagnostic fuel attributed to the observed activity stays
zero and corridor diagnostics retain their explicitly labeled arithmetic
behavior. At pair level, zero-work observations
are excluded whenever positive work exists; the all-zero case uses the labeled
ordinary-median fallback above.

For routes backed by directional ANTAQ+MRV observations, the single-evaluation
pipeline JSON exposes the selected sublegs under
`results.multimodal.sea.selected_corridor_sublegs` and keeps the compatible
`observed_port_pair_legs` view. Each selected subleg separates the historical
corridor intensity (`observed_corridor_fuel_g_per_tnm`) from the pair value
actually applied to scenario cargo (`scenario_fuel_g_per_tnm`). Pair-level
fields record the estimator, scope, transport-work total, effective voyage
count, source counts, and the selected corridor's original intensity.

The explicit `pair_intensity_*` fields are canonical for scenario intensity.
The legacy `fuel_g_per_tnm_weighted_mean` field keeps its original selected-
corridor weighted-mean meaning, and evaluated sublegs keep their historical
`fuel_g_per_tnm`; scenario values use the separate `scenario_fuel_g_per_tnm`
field. The directional metadata declares `maritime_intensity_schema_version=3`
and a generation timestamp so a complete newer tracked contract can replace an
older or partially upgraded cache.

The usual pair source is
`antaq_mrv_same_od_transport_work_weighted_median`. In the all-zero-work case,
the source changes explicitly to
`antaq_mrv_same_od_unweighted_median_zero_transport_work`; the validator and
runtime accept zero transport work only for that labeled method.

`attributed_cargo_t` is the scenario input (14 t for a 14 t evaluation), not a
hard-coded constant. It must not be confused with the reconstructed ANTAQ cargo
aboard used to derive transport work and fuel attributed to the observed voyage
activity.

Voyage intensity resolution is auditable and ordered as follows:

1. latest positive EU MRV transport-work intensity matched by IMO;
2. tracked 1% trimmed mean for an explicitly available vessel class, with the
   class median used only when the trimmed statistic is unavailable;
3. symmetric 1% trimmed mean of latest positive IMO values for an available
   ship type, using `Container ship` as the documented default for the
   containerized ANTAQ scope; samples too small to trim use the median;
4. explicit unresolved status when none of those sources is usable.

Exact IMO matches and class/type fallbacks remain separate in coverage and
source-count indicators. Exact IMO values are preserved without clipping. The
outlier rule applies only to fallback aggregation: sort the positive latest-IMO
values and exclude `floor(0.01 * n)` observations from each tail. Ship-type
fallback provenance stores the raw and retained sample sizes, excluded count,
retained bounds, raw mean, raw median, and statistic actually used. Class
fallback provenance retains the statistic and sample metadata available in its
tracked artifact. This prevents extreme MRV tail values from dominating a
ship-type fallback without rewriting an exact ship-level record.

In the current `Container ship` fallback sample, the rule starts from 243
latest positive IMO values, removes two observations from each tail, and keeps
239 values. The resulting fallback is `9.322050 g/(t*nm)`, compared with the
untrimmed arithmetic mean of `21.661852 g/(t*nm)` and the raw median of
`4.620000 g/(t*nm)`. The 1% rule was already present in the tracked class
artifact and is applied independently of any target route result; it was not
calibrated to reproduce the former Santos--Suape--Manaus calculation.

For Santos--Manaus, the current artifact contains 89 positive-work voyage--OD
observations across 22 corridors. Their transport-work-weighted median is
`9.322050 g/(t*nm)`: 40 observations use an exact IMO match and 49 use the
ship-type fallback. The same value is present on the single direct observation,
but the pair result is controlled by the 49 identical fallback observations
that carry 59.54% of transport work and therefore cross the weighted 50th
percentile. The computational scope covers all 89 same-OD observations, but
this does not make them 89 independent measured fuel intensities. The value
remains 17.6% above the former
`7.926784 g/(t*nm)` calculation; that older value is a comparison reference,
not a calibration target. The unrobust transport-work-weighted arithmetic mean
of all 89 observations would be `25.243618 g/(t*nm)` because of high exact-IMO
values, which is why it is retained only as a diagnostic.

A separate runtime contingency, used only when no transport-work intensity is
available, scales vessel-level fuel by cargo share based on class median
`size_proxy_t`. It is distinct from the class/type MRV fallback above.

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
- `fuel_g_per_tnm`
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
