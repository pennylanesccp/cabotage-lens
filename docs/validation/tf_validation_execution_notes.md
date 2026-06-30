# TF Validation Execution Notes

These notes define the first controlled validation batch for CabotageLens. They translate the candidate sample in `docs/tf_support/validation/tf_validation_plan.md` into an execution-ready planning structure.

This document does not contain validation results. Do not add reference distances, emissions, costs, pass/fail outcomes, or calculated deltas until the validation cases have been run and independently checked.

## Supported Validation Checks

The execution templates are designed to support:

- road distance validation;
- maritime distance validation;
- emissions order-of-magnitude validation;
- cost order-of-magnitude validation;
- route logic validation;
- nearest-port edge cases;
- short and long OD pairs;
- Northern/Amazon-region special cases;
- reproducibility and output audit.

## First Validation Batch

Start with five OD pairs. This batch is intentionally small enough for manual inspection while still covering close-to-port behavior, long coastal corridors, inland access effects, and Northern/Amazon-region special cases.

| Case ID | OD pair | Classification | Why included | Validation checks exercised | Expected risks to inspect |
| --- | --- | --- | --- | --- | --- |
| `TF-VAL-001` | Sao Paulo (SP) -> Santos (SP) | Edge case | Origin and destination are close to a major port region, so cabotage should usually be inappropriate for the main interpretation. | Road distance validation; close-to-port behavior; cabotage-inappropriate route check; reproducibility and output audit. | Geocoding may resolve to city centroids rather than freight-relevant points; selected port access distances may dominate interpretation; route logic must not imply a meaningful cabotage alternative for a local movement. |
| `TF-VAL-002` | Sao Paulo (SP) -> Manaus (AM) | Main validation case | Long corridor with strong road-versus-cabotage relevance and Amazon-region complexity. | Road distance validation; maritime distance validation; route logic validation; emissions order-of-magnitude validation; cost order-of-magnitude validation; Northern/Amazon-region special handling; reproducibility and output audit. | Road references may differ because of ferry, river, or constrained access assumptions; maritime leg may require corridor or river-sensitive interpretation; fallback distance or vessel-class flags must be visible before conclusions are drawn. |
| `TF-VAL-003` | Manaus (AM) -> Fortaleza (CE) | Main validation case | Northern/coastal route from the thesis benchmark context, useful for inspecting Amazon-origin routing and port selection. | Maritime distance validation; route logic validation; port selection review; emissions order-of-magnitude validation; Northern/Amazon-region special handling; reproducibility and output audit. | Manaus access and river/coastal routing may not fit a simple direct coastal abstraction; nearest feasible port and service plausibility need manual review; reference sources may use different intermediate-stop assumptions. |
| `TF-VAL-004` | Brasilia (DF) -> Salvador (BA) | Main validation case | Inland origin to coastal destination, included to test whether access-leg distances and selected ports remain geographically coherent. | Road distance validation; route logic validation; nearest-port edge case check; far-from-port access-leg review; cost order-of-magnitude validation; reproducibility and output audit. | Nearest-port selection may be geometrically convenient but operationally weak; pre-carriage distance can materially affect multimodal conclusions; comparison sources may use different urban access or terminal boundaries. |
| `TF-VAL-005` | Porto Alegre (RS) -> Recife (PE) | Stress test | Long national-scale coastal corridor with a large maritime component, useful for checking scaling of distance, emissions, and cost outputs. | Maritime distance validation; extreme long-distance check; emissions order-of-magnitude validation; cost order-of-magnitude validation; route logic validation; reproducibility and output audit. | Long-route outputs may reveal unit conversion, fallback, or accumulation errors; port-pair reference may require schedule or corridor interpretation; conclusions may be sensitive to fuel prices, maritime intensity, and port-operation assumptions. |

## Execution Procedure

For each case:

1. Create or update one row in `docs/validation/tf_validation_sample_template.csv` after the run artifact exists.
2. Complete one run manifest entry using `docs/validation/tf_validation_run_manifest.md`.
3. Save the exact command or input payload used for the case.
4. Record resolved coordinates, selected ports, all route distance components, maritime distance source, route cache status, and fallback flags.
5. Record fuel prices, fuel price dates, emission factors, cost boundary, and emissions boundary before comparing outputs.
6. Collect independent road and maritime references before assigning a validation status.
7. Classify any failure or limitation as a data issue, model-boundary mismatch, operational plausibility issue, or sensitivity-analysis requirement.

## Status Vocabulary

Use controlled status labels consistently across the sample template and completed manifests:

- `not_run`: case is planned but no model output has been generated.
- `reference_needed`: model output exists but independent references are incomplete.
- `pass`: result is plausible under the stated boundary and references.
- `pass_with_limitation`: result is usable with documented caveats or confidence downgrade.
- `fail_data_issue`: failure appears caused by wrong data, coordinates, unit conversion, or distance entry.
- `fail_boundary_mismatch`: comparison source uses a different route, cost, or emissions boundary.
- `fail_operational_plausibility`: route chain is not plausible enough for main thesis conclusions.
- `sensitivity_required`: route is plausible but conclusion depends materially on uncertain assumptions or fallback values.

## Data Discipline

- Do not populate numeric result columns until a controlled execution has been run.
- Do not invent independent reference distances, emissions, costs, fuel prices, or validation outcomes.
- Keep road distance in kilometres, maritime distance in nautical miles unless explicitly converted, emissions in kg CO2e, and costs in BRL.
- Record whether a maritime value came from a matrix, observed/corridor source, or fallback approximation.
- Treat Northern and Amazon-region cases as special unless the route abstraction is independently justified.
