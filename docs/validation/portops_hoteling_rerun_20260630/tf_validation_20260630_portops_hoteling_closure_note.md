# Validation Closure Note - 20260630 Port-Ops/Hoteling Rerun

Closure status: audited only on 2026-06-30. The validation batches were not rerun, and no historical validation artifacts were overwritten.

## Current Artifacts

The current final artifacts for this closure pass are the files under `docs/validation/portops_hoteling_rerun_20260630/` with the `20260630_portops_hoteling` label:

- `tf_validation_batch_001b_sensitivity_20260630_portops_hoteling.csv`
- `tf_validation_batch_001b_sensitivity_20260630_portops_hoteling.json`
- `tf_validation_batch_002_gustavo_20260630_portops_hoteling.csv`
- `tf_validation_batch_002_gustavo_20260630_portops_hoteling.json`
- `tf_validation_20260630_portops_hoteling_routes.csv`
- `tf_validation_20260630_portops_hoteling_delta.csv`
- `tf_validation_20260630_portops_hoteling_summary.json`
- `tf_validation_20260630_portops_hoteling_summary.md`

The summary artifact records generation at `2026-06-30T18:04:27-03:00` from git SHA `4d900b401bc591bdec59b9868777e80265ae52b4`. The closure audit was performed against current `main` at `d7338cf33a3f844fb3bd87419c8dd50fdb526a1b`.

## Rerun Decision

No new validation rerun was generated. Post-generation backend changes were inspected. They harden port-operations provenance, unavailable-value handling, explicit zero-move behavior, and non-positive cargo handling. The modeled validation rows audited here all use positive cargo activity (`cargo_t=14.0` and `teu`/`cargo_teu=1.0`) with maritime transport-work intensity active, so the later zero-cargo and explicit-zero safeguards do not change this validation scope.

The existing artifacts remain valid for the current final-report interpretation because the route-level CSV, summary JSON, and batch CSVs already expose the required component/provenance fields for the modeled rows:

- navigation emissions;
- explicit hoteling emissions;
- hoteling inclusion/exclusion reason;
- port-operations emissions;
- port-operations source level and warnings;
- component-total reconciliation fields;
- road-vs-cabotage savings and emissions winner fields.

## Checks Used

Commands/scripts used in this closure pass:

- Inline Python artifact audit using `.\venv\Scripts\python.exe -` to open all expected CSV, JSON, and Markdown files, recompute aggregates, recompute component totals, recompute savings percentages, recompute emissions winners, and verify provenance fields.
- `git diff --name-status 4d900b401bc591bdec59b9868777e80265ae52b4..HEAD -- scripts modules tests docs\validation`
- `.\venv\Scripts\python.exe -m unittest tests.test_validation_batch_001b tests.test_port_ops_fallback tests.test_multimodal_evaluator tests.test_docs_port_ops_provenance tests.test_main_details`
- `.\venv\Scripts\python.exe -m compileall scripts modules`
- `git diff --check`

Generation scripts associated with the current artifacts were inspected but not rerun:

- `scripts/run_validation_batch_001b.py`
- `scripts/benchmark_gustavo_excel.py`
- `scripts/summarize_validation_portops_hoteling_rerun.py`

## Confirmed Aggregate Results

- Route rows in combined route artifact: 29.
- Executed/model rows: 24.
- Batch 001B sensitivity executed rows: 3.
- Batch 002 Gustavo/Costa benchmark rows: 21.
- Mean road emissions: 6258.34 kg CO2e.
- Mean cabotage/multimodal emissions: 467.43 kg CO2e.
- Mean cabotage savings: 91.97%.
- Navigation emissions sum: 8586.80 kg CO2e.
- Explicit hoteling emissions sum: 0.00 kg CO2e.
- Port-operations emissions sum: 309.72 kg CO2e.
- Emissions winner count: 24 `cabotage_lower_emissions`.
- Modal conclusion changes: 0.

## Reconciliation Status

For every executed/model row, the audited component equation reconciles:

`pre_carriage_emissions_kgco2e + navigation_emissions_kgco2e + hoteling_emissions_kgco2e + port_ops_emissions_kgco2e + on_carriage_emissions_kgco2e = cabotage_emissions_kgco2e`

The maximum absolute component residual was `2.27e-13` kg CO2e, consistent with floating-point roundoff. The maximum savings-percentage residual was `1.42e-14` percentage points.

## Component And Provenance Findings

- Hoteling was requested in all 24 executed/model rows.
- Separate hoteling emissions were not added in any executed/model row.
- Hoteling exclusion reason was `included_in_transport_work_intensity` in all 24 executed/model rows.
- Port operations were included in all 24 executed/model rows.
- Port-operations source level was `literature_default` in all 24 executed/model rows.
- The port-operations fallback/default is explicit through source-level fields and warnings; it is not a silent zero.
- No observed port-level records or estimated observed-port averages are represented in this rerun.

## Interpretation Limits

- The Batch 001B old-versus-new deltas must not be interpreted as pure port-operations/hoteling methodology effects because route-cache/provider-resolved road legs also changed between the previous tracked output and this rerun.
- The port-operations values in this rerun use the documented moves-based literature/default scenario, not observed per-port operational records.
- The zero hoteling component means separate hoteling was suppressed to avoid double counting under transport-work fuel intensity; it does not mean hoteling activity is physically impossible or irrelevant.
- The aggregate conclusions above apply only to the 24 executed/model rows, not to record-only, blocked, or excluded Batch 001B rows.

Final-report use: the final report can reference these artifacts for the stated validation scope, provided the interpretation limits above are preserved.
