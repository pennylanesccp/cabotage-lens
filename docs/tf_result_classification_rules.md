# Result Classification Rules

## 1. Purpose

This document defines practical rules for interpreting CabotageLens results in the final undergraduate thesis/report. The goal is to avoid overclaiming by classifying each origin-destination pair or corridor according to metric size, sensitivity behavior, validation quality, and operational plausibility.

This is a methodology planning note only. It does not run calculations, report results, or assign classifications to actual routes.

This note should be read together with `docs/tf_assumptions_and_approximations.md`, `docs/tf_validation_plan.md`, and `docs/tf_sensitivity_analysis_plan.md`. The planning files `docs/tf_document_structure.md`, `docs/tf_system_boundary.md`, and `docs/tf_data_reliability_inventory.md` were not present in the repository when this note was prepared.

## 2. Core comparison metrics

The final thesis should classify cost and emissions separately before making a combined conclusion. A route can be robustly lower-emission but cost-sensitive, or cost-favorable but emissions-inconclusive.

### Primary metrics

- Total cost difference between road-only and multimodal, in BRL per shipment or per selected unit.
- Total emissions difference between road-only and multimodal, in kg CO2e per shipment or per selected unit.
- Percentage cost savings or increase:
  - `(road_cost - multimodal_cost) / road_cost`
  - Positive value means multimodal is lower-cost.
  - Negative value means road-only is lower-cost.
- Percentage emissions savings or increase:
  - `(road_emissions - multimodal_emissions) / road_emissions`
  - Positive value means multimodal is lower-emission.
  - Negative value means road-only is lower-emission.

### Distance and route-shape metrics

- Road-only distance, in km.
- Pre-carriage road distance, in km.
- Sea distance, in km and/or nautical miles, with conversion documented when needed.
- On-carriage road distance, in km.
- Access-leg share:
  - `(pre_carriage_road_km + on_carriage_road_km) / total_multimodal_distance_km`
- Distance source flags:
  - API/cache road distance.
  - Matrix, observed/corridor, or fallback maritime distance.

### Optional normalized metrics

Use normalized metrics when comparing across cargo sizes or corridors of different length.

- Emissions per tonne, in kg CO2e/t.
- Emissions per tonne-kilometer, in kg CO2e/tkm.
- Maritime emissions per tonne-nautical-mile, where appropriate and dimensionally consistent.
- Cost per tonne, in BRL/t.
- Cost per tonne-kilometer, in BRL/tkm.

Normalized values should not replace per-shipment totals. They are supporting interpretation metrics.

## 3. Classification rules

### Robust cabotage advantage

Use this class when multimodal road-cabotage-road remains better than road-only for the selected metric after validation and sensitivity checks.

Evidence needed:

- Base result favors multimodal by a meaningful margin.
- Sensitivity analysis does not reverse the result under plausible road-favorable assumptions.
- Route logic is geographically and operationally plausible.
- Distance, emissions, and cost inputs pass validation or are supported by acceptable references.
- Major fallback use is either absent or clearly shown not to drive the conclusion.

Final thesis wording:

> For this corridor and boundary, the multimodal alternative shows a robust advantage over road-only transport for [cost/emissions]. The conclusion remains valid across the tested sensitivity scenarios and is supported by acceptable validation evidence.

### Robust road advantage

Use this class when road-only remains better than multimodal for the selected metric after validation and sensitivity checks.

Evidence needed:

- Base result favors road-only by a meaningful margin.
- Sensitivity analysis does not reverse the result under plausible cabotage-favorable assumptions.
- Multimodal chain is either operationally plausible but less favorable, or access/port constraints make road-only structurally stronger.
- Distance and cost/emissions inputs pass validation or are adequately documented.

Final thesis wording:

> For this corridor and boundary, road-only transport shows a robust advantage over the modeled multimodal alternative for [cost/emissions]. The result is not reversed by the tested cabotage-favorable assumptions.

### Sensitive cabotage advantage

Use this class when the base result favors multimodal, but the advantage depends on uncertain parameters or changes under plausible sensitivity cases.

Evidence needed:

- Base result favors multimodal.
- At least one plausible sensitivity case materially weakens or reverses the advantage, or validation uncertainty is large relative to the base margin.
- Route logic is not invalid, but one or more assumptions needs cautious interpretation.

Final thesis wording:

> The base case favors multimodal transport for [cost/emissions], but the conclusion is sensitive to assumptions such as [parameter]. The result should be interpreted as a conditional advantage rather than a robust finding.

### Sensitive road advantage

Use this class when the base result favors road-only, but the advantage depends on uncertain parameters or changes under plausible sensitivity cases.

Evidence needed:

- Base result favors road-only.
- At least one plausible sensitivity case materially weakens or reverses the road advantage.
- Route logic is not invalid, but uncertainty in assumptions prevents a robust conclusion.

Final thesis wording:

> The base case favors road-only transport for [cost/emissions], but the conclusion is sensitive to assumptions such as [parameter]. The result should be interpreted as conditional rather than definitive.

### Inconclusive result

Use this class when the difference between alternatives is too small relative to uncertainty, validation tolerance, or sensitivity behavior.

Evidence needed:

- Base difference is small, or cost and emissions rankings conflict in a way that cannot be resolved under the stated objective.
- Sensitivity cases change the result or leave alternatives effectively tied.
- Validation uncertainty is comparable to the reported difference.
- Route is plausible enough to evaluate, but the evidence does not support a strong ranking.

Final thesis wording:

> The modeled alternatives are too close, or too sensitive to uncertain parameters, to support a definitive conclusion for this corridor. The result is therefore classified as inconclusive under the current model boundary.

### Out-of-scope / invalid case

Use this class when the route, data, or operational logic is insufficient for a defensible comparison.

Evidence needed:

- Geocoding or routing is incorrect or unresolved.
- Selected ports are not operationally plausible for the corridor.
- Maritime distance or intensity relies on unsupported fallback assumptions that dominate the result.
- The OD pair requires inland waterway, ferry, service-network, or terminal logic outside the model scope.
- The route is clearly inappropriate for cabotage, such as very short local movement with artificial port use.

Final thesis wording:

> This case is not used as evidence for modal comparison because the route or data quality is outside the validated model scope. It is retained only as a limitation, stress test, or future-work example.

## 4. Suggested planning thresholds

The thresholds below are adjustable planning thresholds, not final universal truth. They should be reviewed after validation and sensitivity analysis, and they should not override operational plausibility or data-quality checks.

| Base percentage difference | Initial interpretation | Required treatment |
| --- | --- | --- |
| Less than 5% absolute difference | Treat as inconclusive unless validation is very strong and sensitivity does not change the result. | Report cautiously; avoid strong claims. |
| 5% to 10% absolute difference | Treat as cautious or sensitive by default. | Require sensitivity analysis and validation evidence before calling meaningful. |
| More than 10% absolute difference | Potentially meaningful. | Still check sensitivity, distance validation, cost/emissions boundary, and route plausibility. |
| More than 25% absolute difference | Potentially strong if validated. | Confirm units, fallbacks, and assumptions because large differences can also indicate modeling artifacts. |

Additional threshold guidance:

- If cost and emissions classifications disagree, report them separately rather than forcing one overall winner.
- If the preferred mode changes under plausible sensitivity scenarios, classify the result as sensitive even if the base difference is above 10%.
- If route validation fails, classify as out-of-scope/invalid regardless of percentage difference.
- If validation uncertainty is larger than the base difference, classify as inconclusive.
- If the result depends on unsupported cost-boundary expansion, classify as methodology debt or sensitive, not robust.

## 5. Relationship with sensitivity analysis

Classification should use the sensitivity-analysis outcome as a gating step.

- Robust: The preferred mode remains better across plausible low/base/high ranges and across the relevant road-favorable or cabotage-favorable scenario.
- Sensitive: The preferred mode changes, or the advantage becomes small enough to be non-decisive, under plausible scenarios.
- Inconclusive: The base difference is smaller than uncertainty, validation error, or sensitivity spread.
- Invalid/out-of-scope: Route logic, geocoding, distance source, maritime coverage, or service plausibility is insufficient for a defensible comparison.
- Boundary-dependent: The classification applies only to the stated boundary, such as fuel-only cost, tank-to-wheel emissions, no empty backhaul, or nearest-port geometry.

Sensitivity should be interpreted separately for cost and emissions:

- Cost sensitivity is expected to be strongly affected by diesel price, bunker price, and cost-boundary assumptions.
- Emissions sensitivity is expected to be strongly affected by truck fuel consumption, maritime fuel intensity, distance assumptions, empty backhaul, hoteling, port operations, and emission factors.
- Carbon price or emissions monetization, if used, should not be allowed to obscure the physical emissions classification.

## 6. Validation and evidence requirements

Each classification should carry a validation status.

Suggested validation status labels:

- Validated: independent checks support the relevant distances, route logic, and order-of-magnitude outputs.
- Partially validated: some components are checked, but at least one major component remains uncertain.
- Unvalidated: route or parameter sources have not yet been checked against independent evidence.
- Failed validation: at least one major validation check failed and was not corrected.
- Out-of-scope: route structure or data quality is outside the validated model boundary.

Classification guidance:

- Robust classes should normally require `Validated` or strong `Partially validated` status.
- Sensitive classes can use `Partially validated` status if the uncertainty is explicit.
- Inconclusive results can be valid results when evidence is adequate but differences are small.
- Out-of-scope/invalid cases should not be promoted to robust or sensitive findings.

## 7. Output table template

Use one row per OD pair or corridor. Cost and emissions can be classified in the same table if the wording keeps them distinct.

| OD pair | Base cost result | Base emissions result | Sensitivity behavior | Validation status | Classification | Recommended wording |
| --- | --- | --- | --- | --- | --- | --- |
| Example OD pair | BRL difference and percent difference; do not fill until results are run. | kg CO2e difference and percent difference; do not fill until results are run. | Robust, sensitive, reversed, or not tested. | Validated, partially validated, unvalidated, failed validation, or out-of-scope. | Robust cabotage advantage, robust road advantage, sensitive cabotage advantage, sensitive road advantage, inconclusive, or out-of-scope/invalid. | One cautious sentence tied to the chosen class. |

Recommended supporting columns when space allows:

- Road-only distance in km.
- Pre-carriage road distance in km.
- Sea distance in km or nm.
- On-carriage road distance in km.
- Maritime distance source.
- Maritime intensity source.
- Hoteling treatment.
- Port-ops treatment.
- Cost boundary.
- Emissions boundary.
- Main sensitivity driver.

## 8. Recommended thesis wording by classification

### Robust cabotage advantage

> The result is classified as a robust cabotage advantage for [cost/emissions] because the multimodal alternative remains better than road-only transport under the tested plausible parameter ranges and passes the relevant validation checks.

### Robust road advantage

> The result is classified as a robust road advantage for [cost/emissions] because road-only transport remains better than the modeled multimodal alternative under the tested plausible parameter ranges and passes the relevant validation checks.

### Sensitive cabotage advantage

> The base case indicates a cabotage advantage for [cost/emissions], but the result is sensitive to [parameter or boundary]. The conclusion should therefore be interpreted as conditional, not definitive.

### Sensitive road advantage

> The base case indicates a road advantage for [cost/emissions], but the result is sensitive to [parameter or boundary]. The conclusion should therefore be interpreted as conditional, not definitive.

### Inconclusive result

> The result is classified as inconclusive because the difference between alternatives is small relative to uncertainty, validation tolerance, or sensitivity spread. The current evidence does not support a definitive modal ranking for this corridor.

### Out-of-scope / invalid case

> This case is excluded from substantive modal conclusions because route logic, data quality, or operational plausibility is outside the validated model boundary.

## 9. Methodology debts

- Review the 5%, 10%, and 25% planning thresholds after validation results and sensitivity ranges are available.
- Decide whether cost and emissions receive separate classifications in all thesis tables or whether a combined narrative category is also needed.
- Define a final validation-status vocabulary and apply it consistently to every OD pair.
- Ensure all result tables expose the cost boundary and emissions boundary.
- Ensure all robust claims identify whether they depend on route-observed maritime intensity, corridor aggregation, class fallback, or another fallback.
- Define how to classify cases where cabotage is lower-emission but higher-cost, or lower-cost but higher-emission.
- Document how invalid/out-of-scope cases are excluded from aggregate results.
