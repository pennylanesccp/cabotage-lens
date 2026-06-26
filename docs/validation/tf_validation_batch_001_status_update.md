# Batch 001 Status Update

## 1. Purpose

This document converts the external reference evidence collected after Batch 001 into recommended preliminary validation statuses for each case. It is a status-update layer only: it does not change the original model outputs recorded in `docs/validation/tf_validation_batch_001_results.md`, does not rerun any model case, and does not add new distance, cost, emissions, or service values.

The recommendations below should be read as defended preliminary classifications for thesis planning. They are not replacements for the raw Batch 001 execution record and should not be treated as full validation of numerical model outputs.

## 2. Status vocabulary

This update uses only the validation labels already defined in the Batch 001 validation notes:

- `reference_needed`
- `pass_with_limitation`
- `fail_boundary_mismatch`
- `fail_operational_plausibility`
- `sensitivity_required`

No case is upgraded to full `pass`. Where evidence is mixed, the recommended status uses the most conservative defensible label. In practice, this means that operational port-service problems take priority over favorable model outputs, unresolved port substitutions remain `reference_needed`, and plausible corridors with unresolved distance bases require sensitivity rather than a stronger validation conclusion.

## 3. Batch-level decision

- All maritime model distances in Batch 001 used `SeaMatrix haversine fallback`. This remains the main batch-level limitation because fallback great-circle or simplified distances do not by themselves defend operational sailing distances.
- Santos -> Manaus has strong service plausibility, but the model's fallback-based maritime distance is much lower than the ANTAQ-based nautical-mile matrix reference described in the external evidence. The corridor is plausible; the distance basis is not yet defensible for a strong thesis conclusion.
- Manaus -> Fortaleza has partial service plausibility for the Fortaleza/Manaus region, but the exact model-selected `Porto de Manaus` -> `Porto de Fortaleza` port pair remains unresolved. Pecem appears as an important nearby comparator and should not be silently substituted for Fortaleza.
- Brasilia -> Salvador selected `Porto de Angra dos Reis` as the origin port. External port-authority evidence says Angra dos Reis has no container movement, so the selected road-sea-road chain is not operationally defensible for the 1 TEU / 14 t benchmark cargo.
- Porto Alegre -> Recife has stronger evidence for `Porto do Rio Grande` -> Suape than for `Porto do Rio Grande` -> `Porto do Recife`. The model-selected destination port should not be silently replaced without an explicit alternate-port scenario.
- Emissions and cost comparisons remain boundary-level only. They may support model-boundary discussion, but they should not be treated as externally validated numerical results until distance, service, and boundary compatibility have been resolved.

## 4. Case-by-case recommended status

### `TF-VAL-001`: Sao Paulo (SP) -> Santos (SP)

Previous status from Batch 001: `reference_needed`

Recommended new preliminary status: `pass_with_limitation`

Evidence supporting the recommendation:

- The model selected `Porto de Santos` as both origin and destination port.
- The maritime leg was recorded as `0.0 km sea` using `SeaMatrix haversine fallback`.
- The external interpretation is consistent with a close-to-port / same-port edge case, not with a meaningful cabotage corridor.

Missing evidence:

- Independent road-distance confirmation for the local Sao Paulo -> Santos movement, if the case remains in any quantitative table.
- A documented route rule for excluding or specially labeling same-port cabotage-inappropriate movements.

Thesis interpretation:

This case can support the thesis only as a route-logic limitation. It validates the need for a cabotage-inappropriate route rule; it does not validate a road-sea-road alternative.

Recommended next action:

Document a same-port exclusion or warning rule for OD pairs where origin and destination resolve to the same cabotage port. Keep the original Batch 001 output unchanged and use the case as a route-logic edge case.

### `TF-VAL-002`: Sao Paulo (SP) -> Manaus (AM)

Previous status from Batch 001: `reference_needed`

Recommended new preliminary status: `sensitivity_required`

Evidence supporting the recommendation:

- The selected ports, `Porto de Santos` -> `Porto de Manaus`, are operationally plausible for a cabotage/coastal-river thesis corridor.
- External evidence indicates strong service plausibility for the Santos -> Manaus corridor.
- The model maritime distance was based on `SeaMatrix haversine fallback`, and the external ANTAQ-based nautical-mile matrix reference indicates a much larger corridor distance than the model value.

Missing evidence:

- A defended replacement or bounded range for the Santos -> Manaus maritime distance.
- A documented nautical-mile to kilometre treatment and route-boundary comparison.
- Sensitivity results showing whether the model's emissions and cost conclusions survive a corrected or bounded maritime distance.

Thesis interpretation:

The selected ports and corridor are plausible, but the distance basis is not yet defensible for a strong thesis conclusion. The case can support a sensitivity discussion, not a validated quantitative advantage.

Recommended next action:

Replace or bound the fallback maritime distance using the ANTAQ-based matrix reference and run a sensitivity plan before changing the original results status.

### `TF-VAL-003`: Manaus (AM) -> Fortaleza (CE)

Previous status from Batch 001: `reference_needed`

Recommended new preliminary status: `reference_needed`

Evidence supporting the recommendation:

- The selected ports were `Porto de Manaus` -> `Porto de Fortaleza`.
- External evidence indicates partial service plausibility for the Fortaleza/Manaus region.
- Pecem appears as an important nearby comparator in the external evidence, which strengthens the need to resolve the exact destination-port assumption.

Missing evidence:

- Exact maritime distance or service evidence for `Porto de Manaus` -> `Porto de Fortaleza`.
- A defended decision on whether the thesis case should use Fortaleza, Pecem, or an explicit alternate-port sensitivity.
- Boundary notes for any source that refers to the broader Fortaleza region rather than the model-selected port.

Thesis interpretation:

This case remains unresolved. Pecem must not be silently substituted for Fortaleza, and regional service plausibility is not enough to validate the model-selected port pair.

Recommended next action:

Collect or document exact Manaus -> Fortaleza evidence, or create an alternate-port sensitivity that explicitly separates Fortaleza and Pecem.

### `TF-VAL-004`: Brasilia (DF) -> Salvador (BA)

Previous status from Batch 001: `reference_needed`

Recommended new preliminary status: `fail_operational_plausibility`

Evidence supporting the recommendation:

- The model selected `Porto de Angra dos Reis` as the origin port and `Porto de Salvador` as the destination port.
- External port-authority evidence says Angra dos Reis has no container movement.
- The Batch 001 benchmark cargo is a 1 TEU / 14 t case, so container suitability is material to operational plausibility.

Missing evidence:

- A defensible alternate origin port for the Brasilia -> Salvador road-sea-road chain.
- Evidence that any alternate port has container service relevance under the benchmark cargo boundary.
- A rerun or sensitivity scenario using the alternate port, if the case is kept in the validation set.

Thesis interpretation:

Road distances may be plausible, but the selected road-sea-road chain is not operationally defensible under the current container benchmark. This case should not support thesis conclusions in its current model-selected form.

Recommended next action:

Replace Angra dos Reis with a defensible alternate port through an explicit alternate-port scenario, or exclude the case from thesis-supporting validation conclusions.

### `TF-VAL-005`: Porto Alegre (RS) -> Recife (PE)

Previous status from Batch 001: `reference_needed`

Recommended new preliminary status: `reference_needed`

Evidence supporting the recommendation:

- The selected ports were `Porto do Rio Grande` -> `Porto do Recife`.
- External evidence supports Rio Grande cabotage relevance and indicates stronger evidence for Rio Grande -> Suape than for Rio Grande -> Recife.
- The model maritime distance was based on `SeaMatrix haversine fallback`.

Missing evidence:

- Exact Rio Grande -> Recife distance or service evidence.
- A defended decision on whether the destination should remain Recife or shift to Suape through an explicit alternate-port scenario.
- Sensitivity or comparison notes if Suape is used as a nearby operational comparator.

Thesis interpretation:

This case may become useful after an explicit Recife-vs-Suape decision or alternate-port sensitivity. Until then, the model-selected destination port should not be silently replaced by Suape.

Recommended next action:

Decide whether the validation case is Rio Grande -> Recife or an alternate Rio Grande -> Suape scenario, then collect or bind the maritime distance and service evidence for the chosen port pair.

## 5. Consolidated table

| Case ID | OD pair | Previous status | Recommended status | Main reason | Can support thesis conclusion now? | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `TF-VAL-001` | Sao Paulo (SP) -> Santos (SP) | `reference_needed` | `pass_with_limitation` | Same-port close-to-port edge case; useful for a cabotage-inappropriate route rule, not for a road-sea-road corridor. | yes, with limitation | Document same-port exclusion or warning rule. |
| `TF-VAL-002` | Sao Paulo (SP) -> Manaus (AM) | `reference_needed` | `sensitivity_required` | Corridor and ports are plausible, but fallback maritime distance conflicts with the ANTAQ-based nautical-mile matrix reference. | no, needs maritime distance correction | Replace or bound Santos -> Manaus maritime distance and run sensitivity. |
| `TF-VAL-003` | Manaus (AM) -> Fortaleza (CE) | `reference_needed` | `reference_needed` | Regional service plausibility exists, but exact Manaus -> Fortaleza evidence is unresolved and Pecem cannot be substituted silently. | no, needs more references | Resolve Fortaleza versus Pecem and collect exact port-pair evidence. |
| `TF-VAL-004` | Brasilia (DF) -> Salvador (BA) | `reference_needed` | `fail_operational_plausibility` | Angra dos Reis was selected as origin port, but external evidence says it has no container movement. | no, needs alternate-port scenario | Replace Angra dos Reis with a defensible alternate port or exclude the case. |
| `TF-VAL-005` | Porto Alegre (RS) -> Recife (PE) | `reference_needed` | `reference_needed` | Rio Grande and Pernambuco/Suape evidence are plausible, but exact Rio Grande -> Recife evidence is missing. | no, needs alternate-port scenario | Decide Recife versus Suape and create an explicit alternate-port sensitivity if needed. |

## 6. Recommended next issue

Recommended next issue:

`Create alternate-port and maritime-distance correction plan for Batch 001`

The next issue should focus on:

- replacing or bounding `SeaMatrix haversine fallback` for Santos -> Manaus;
- deciding whether Manaus -> Fortaleza should use Fortaleza or Pecem;
- replacing Angra dos Reis with a defensible alternate port for Brasilia -> Salvador, or excluding the case;
- deciding whether Porto Alegre -> Recife should use Recife or Suape;
- documenting a same-port exclusion rule for Sao Paulo -> Santos.

The issue should remain documentation and methodology planning first. Model reruns should occur only after the alternate-port and maritime-distance correction assumptions are explicit enough to defend academically.
