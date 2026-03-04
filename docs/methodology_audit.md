# Methodology Audit

## Scope

Audit date: 2026-03-04.

This audit checks the current pipeline against:

- repo references under `references/`
- EU MRV workbook source fields used in preprocessing
- EMEP/EEA Guidebook 2023 assumptions already used in `docs/hoteling_model.md`

The focus is methodological consistency and traceability, not feature redesign.

## 1) Inventory of References

Notes:

- For a subset of PDFs, metadata extraction is limited by document encoding.
- When full text was not machine-readable, classification below relies on filename/title metadata and should be treated as provisional.
- "Cited/used in docs" means explicit file-level citation in current repo docs.

### `references/seagoing_ships_at_berth_fuel_emissions_survey_2009.pdf`

- Covers:
  - At-berth fuel consumption and associated emissions from seagoing ships.
  - Survey-based hotelling behavior evidence.
- Pipeline support:
  - Hoteling limitations and sanity checks.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite in `docs/hoteling_model.md` limitations section (boilers/auxiliary variability by port).

### `references/biodiesel_brazil_history_environment_review_2017.pdf`

- Covers:
  - Biodiesel evolution and environmental context in Brazil.
- Pipeline support:
  - Road fuel decarbonization context (not current TTW core logic).
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Keep as background; use only if adding biodiesel blend sensitivity scenarios.

### `references/brazil_coastal_shipping_decarbonization_icct_2022.pdf`

- Covers:
  - Brazilian coastal shipping growth and decarbonization framing.
- Pipeline support:
  - Cabotage policy and adoption context.
- Cited/used in docs:
  - Partial conceptual mention in `README.md` (ICCT Jul/2022), not file-cited.
- Recommendation:
  - Add explicit file citation in `README.md` and in scenario framing docs.

### `references/brazilian_cabotage_competitiveness_supernetwork_2024.pdf`

- Covers:
  - Multimodal supernetwork competitiveness for Brazilian cabotage.
- Pipeline support:
  - Network-level model framing and mode-shift interpretation.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite in methodology rationale section as external validation context.

### `references/brazilian_cabotage_user_satisfaction_assessment_2022.pdf`

- Covers:
  - User satisfaction in Brazilian container cabotage.
- Pipeline support:
  - Service-level context, not emissions core equations.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Keep for background and discussion, not core model calibration.

### `references/brazilian_cabotage_decarbonization_pathways_fuels_2024_alt.pdf`

- Covers:
  - HVO/decarbonization topic by filename; embedded text is weak.
- Pipeline support:
  - Alternative marine fuel pathway context.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Mark as provisional in references until full bibliographic metadata is recovered.

### `references/short_sea_container_co2_efficiency_comparison_2019.pdf`

- Covers:
  - Comparative CO2 efficiency in short-sea container transport.
- Pipeline support:
  - Sea-leg efficiency plausibility checks versus literature ranges.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite in `docs/mrv_container_efficiency.md` discussion of class medians.

### `references/Dados Relatorio 2.xlsx`

- Covers:
  - Scenario workbook with sheets for emissions factors, road/cabotage scenarios, and terminal operations.
- Pipeline support:
  - Primary parameter source for moves-based port-ops factors (`RTG Base C1`, `RTG C2`, `TT Base C1`, `TT C2`).
- Cited/used in docs:
  - Yes, in `docs/port_ops_model.md`.
- Recommendation:
  - Keep as processed-input source through `calcs/port_ops_params_builder.py`; add periodic refresh checks if workbook revisions are added.

### `references/brazilian_cabotage_decarbonization_pathways_fuels_2024.pdf`

- Covers:
  - Decarbonization pathways and marine fuel comparisons by filename.
- Pipeline support:
  - Future WTW and fuel-switch scenario design.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite when introducing marine fuel-type scenarios beyond current default.

### `references/eu_mrv_ship_energy_efficiency_framework_review_2025.pdf`

- Covers:
  - EU MRV data-based review of ship energy efficiency framework.
- Pipeline support:
  - Direct support for using MRV observed metrics (`kg/nm`, `t/h`) for empirical calibration.
- Cited/used in docs:
  - No direct file citation.
- Recommendation:
  - Add explicit citation to `docs/mrv_container_efficiency.md` under method validity.

### `references/short_sea_shipping_external_cost_internalization_2022.pdf`

- Covers:
  - External-cost internalization effects in short sea shipping.
- Pipeline support:
  - Extensions to include externality-aware economics.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Keep for future policy-scenario module; not required for current TTW model.

### `references/fast_shapley_approximation_routing_ml_models_2025.pdf`

- Covers:
  - Shapley approximation for routing allocations.
- Pipeline support:
  - Future multi-shipper allocation logic for costs/emissions.
- Cited/used in docs:
  - Partial conceptual mention in `README.md` (Shapley future work), not file-cited.
- Recommendation:
  - Keep as future-work anchor; no immediate runtime integration.

### `references/lifecycle_cost_alt_marine_fuels_short_sea_2020.pdf`

- Covers:
  - Life-cycle cost assessment of alternative marine fuels in short-sea shipping.
- Pipeline support:
  - WTW/LCA extension and fuel-price sensitivity design.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite in future work for WTW expansion beyond TTW-only default.

### `references/maritime_fuels_lca_review_insights_gaps_2024.pdf`

- Covers:
  - LCA review of maritime fuels, gaps, and recommendations.
- Pipeline support:
  - Future WTW factors and uncertainty boundaries.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Use to define WTW methodological guardrails before adding fuel pathway comparisons.

### `references/dry_bulk_shipping_carbon_footprint_mrv_assessment_2019.pdf`

- Covers:
  - Early MRV-based carbon footprint assessment methodology.
- Pipeline support:
  - Supports empirical MRV usage and field interpretation discipline.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Cite in `docs/mrv_container_efficiency.md` as methodological precedent.

### `references/ship_hoteling_loading_unloading_emissions_se_asia_2022.pdf`

- Covers:
  - Hotelling and loading/unloading emissions in port operations.
- Pipeline support:
  - Supports known omissions and potential refinements (cargo ops, berth activity granularity).
- Cited/used in docs:
  - Yes, in `docs/port_ops_model.md`.
- Recommendation:
  - Keep as contextual validation for port-ops granularity gaps.

### `references/rtg_crane_energy_usage_analysis_2017.pdf`

- Covers:
  - RTG energy usage profile and operational efficiency behavior.
- Pipeline support:
  - Supports RTG-focused equipment-level treatment in the port-ops module.
- Cited/used in docs:
  - Yes, in `docs/port_ops_model.md`.
- Recommendation:
  - Use for future non-diesel RTG calibration once site-specific electrical factors are available.

### `references/hybrid_rtg_diesel_battery_energy_management_2021.pdf`

- Covers:
  - Hybrid RTG energy management with reported diesel/CO2 reduction outcomes.
- Pipeline support:
  - Basis for partially-electrified RTG diesel-reduction proxy in `port_ops_params_santos.json`.
- Cited/used in docs:
  - Yes, in `docs/port_ops_model.md`.
- Recommendation:
  - Keep reduction range explicit and scenario-bounded (no single deterministic value).

### `references/fal_329_port_awareness_maritime_emissions_2014.pdf`

- Covers:
  - Port and maritime energy/emissions awareness context in Latin America and the Caribbean.
- Pipeline support:
  - Contextual support for regional port decarbonization framing.
- Cited/used in docs:
  - No direct citation.
- Recommendation:
  - Keep as background reference for policy/context sections.

### `references/desktop.ini`

- Covers:
  - Windows metadata file.
- Pipeline support:
  - None.
- Cited/used in docs:
  - No.
- Recommendation:
  - Ignore.

## 2) Pipeline Check by Module

## `calcs/mrv_container_efficiency.py`

What it does:

- Loads 2021-2024 MRV workbooks.
- Normalizes key columns.
- Filters container ships.
- Derives class proxy (`size_proxy_t`) from MRV transport-work-linked fields.
- Builds class stats for `fuel_per_nm`, `fuel_per_km`, `co2_per_nm`, `size_proxy_t`.
- Builds sea-rate (`t/h`) and derived hoteling-rate artifacts.

Assumptions audit:

- Using MRV observed `fuel_per_nm` and `co2_per_nm` as primary intensity inputs.
  - Status: supported by EU MRV framework and MRV-focused references.
- Using transport-work-linked size proxy instead of technical efficiency.
  - Status: defensible and materially better than EEDI proxy.
- Class thresholds (20k, 40k tonnes proxy) for small/feeder/large.
  - Status: pragmatic assumption from project design; should be explicitly justified in docs as operational classes, not regulatory bins.
- Outlier treatment via class-local trimmed and winsorized means (1% tails).
  - Status: methodologically sound for robust descriptive statistics.

## `modules/multimodal/container_efficiency.py`

What it does:

- Loads class artifact and resolves selected class.
- Uses `fuel_per_nm.median` with fallback order.

Assumptions audit:

- Median is default representative class value.
  - Status: supported after robust stats addition.
- Fallback to `container_feeder`.
  - Status: pragmatic; reasonable for Brazilian cabotage defaults.

## `modules/multimodal/hoteling.py`

What it does:

- Loads hoteling-rate artifact.
- Resolves class median `fuel_rate_hoteling_t_per_h` with fallback.

Assumptions audit:

- Median hotelling rate is default runtime value.
  - Status: supported by robust class stats.
- Fallback behavior mirrors sea-class logic.
  - Status: good runtime resilience.

## `modules/multimodal/evaluator.py`

What it does:

- Computes road-only and multimodal totals.
- Sea sailing fuel: `distance_nm * fuel_per_nm`.
- Hoteling fuel: `hoteling_hours_total * hoteling_rate_t_per_h * 1000`.
- Port-ops fuel/emissions/cost from `modules.multimodal.port_ops.estimate_port_ops(...)`.
- Total sea-side aggregate = sailing + hoteling + port-ops, then cost/emissions.

Assumptions audit:

- Unit chain is consistent (`kg/nm`, `t/h`, `kg`).
  - Status: supported and internally consistent.
- Default hoteling controls (`include=True`, `14 h/call`, `2 calls`).
  - Status: supported by EMEP/EEA default table usage, but Brazil-specific applicability should be treated as a fallback.
- Marine emission factor sourcing.
  - Status: corrected in this update to use `modules.fuel.emissions` canonical factor path (`vlsfo`), removing hardcoded drift risk.

## `modules/multimodal/port_ops.py`

What it does:

- Loads processed moves-based terminal parameters from `data/processed/cabotage_data/port_ops_params_santos.json`.
- Resolves scenario (`santos_diesel_heavy` / `santos_partially_electrified`) with fallback.
- Computes equipment-level moves, diesel liters, fuel mass, electricity, CO2e, and cost.

Assumptions audit:

- Moves-based equipment aggregation (`quay moves` -> RTG/TT multipliers).
  - Status: supported by `references/Dados Relatorio 2.xlsx` structure and transparent in params artifact.
- RTG partially-electrified scenario via diesel-reduction proxy.
  - Status: supported as bounded proxy by `references/hybrid_rtg_diesel_battery_energy_management_2021.pdf`.
- STS factor currently zero placeholder.
  - Status: pragmatic placeholder due missing direct per-move value in provided references.

## Port/Hotelling legacy placeholders (`calcs/hotel.py`, `modules/fuel/cabotage_fuel_service.py`)

What they do:

- Legacy path for per-port hotel factors (`kg/t`) and older sea+ops model.

Assumptions audit:

- These modules use different abstractions than the active MRV-class + hoteling + moves-based port-ops runtime.
  - Status: legacy/non-active; retain only for backward comparisons.
- Recommendation:
  - Mark as legacy/deprecated in README and avoid mixing outputs in active scenarios.

## Road model and emission factors (`modules/fuel/road_fuel_model.py`, `modules/fuel/truck_specs.py`, `modules/fuel/emissions.py`)

What they do:

- Road fuel by axle-based km/L baseline plus linear payload sensitivity.
- Emissions conversion by fuel type with canonical TTW factors.

Assumptions audit:

- ANTT-like axle baselines and deterministic payload heuristics.
  - Status: pragmatic planning model; acceptable for scenario analysis.
- Linear elasticity with no grade/speed/traffic explicit terms.
  - Status: pragmatic simplification; should be documented as such.
- TTW factor tables in `emissions.py`.
  - Status: coherent and now used by evaluator for marine EF.

## 3) Specific Audit Checkpoints

### MRV-derived classing defensibility

- Current proxy is based on carried-work-related MRV fields, not technical efficiency.
- This is defensible for class grouping.
- Caveat: in current run, most rows came from mass-based transport-work intensity fallback; only a small share used dwt-specific intensity, so "size" should be interpreted as a carried-mass proxy.

### MRV fields and unit handling

- `fuel_per_nm` in `kg/nm` is used directly for sailing fuel.
- `fuel_per_km` conversion uses `1 nm = 1.852 km`.
- `fuel_rate_sea_t_per_h` is taken from MRV field or derived from total fuel/time-at-sea.
- Hoteling conversion keeps compatible units (`t/h` -> `kg`).

### Hoteling model interpretation (EMEP/EEA)

- Implemented ratio: `hoteling_rate = sea_rate * ((0.40*r)/(0.80 + 0.30*r))`.
- This is consistent with first-order EMEP/EEA ratio interpretation used in current docs.
- Limitations not modeled: boilers, reefers, shore power uptake, berth power management differences, and explicit STS/electric-grid calibration.

### Port-call defaults and Brazil applicability

- `14 h` default is traceable to EMEP/EEA default table for container hotelling.
- Applicability to Brazilian ports is a fallback assumption, not Brazil-specific calibration.
- Recommendation: allow per-port/per-route override datasets when available.

### Emission factor consistency

- Marine EF now flows from shared `modules/fuel/emissions.py` factor table in evaluator.
- Remaining simplification: fixed marine fuel type (`vlsfo`) in evaluator; no runtime selection between VLSFO/MGO for sea leg.

### Known missing pieces

- Reefer load explicit modeling.
- Boiler load in port phase.
- Shore power scenarios.
- Explicit STS crane per-move energy factor (currently placeholder).
- Site-specific electricity emission and tariff factors for port equipment.
- AIS-based speed/power variability for sea legs.

## 4) Recommendations

## Must-fix

- Add explicit file-level citations in docs for the references already used conceptually (MRV literature, hotelling literature, Brazilian cabotage context).
- Mark legacy `calcs/hotel.py` and `modules/fuel/cabotage_fuel_service.py` as legacy/non-active in README to prevent mixed-method runs.

## Should-improve

- Add explicit uncertainty reporting in UI/CLI using `p10-p90` bands, not only medians.
- Add an optional scenario switch for marine fuel type (`vlsfo` vs `mgo`) in evaluator inputs, with factor sourcing from `modules/fuel/emissions.py`.
- Add a validation notebook comparing model outputs with `references/Dados Relatorio 2.xlsx` scenarios.

## Future work

- Build WTW extension (well-to-tank + tank-to-wake) using maritime fuel LCA references.
- Add reefers/boilers/shore-power submodels for berth emissions.
- Integrate AIS-informed dynamic speed/power for sea-leg and berth activity timing.
