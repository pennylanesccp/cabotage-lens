# Batch 001 Reference Needs

## 1. Purpose

This document maps the independent references required before the Batch 001 validation cases can be upgraded from `reference_needed`.

It uses `docs/validation/tf_validation_batch_001_results.md` as the source for model-selected ports, model distances, maritime distance source flags, and observed execution concerns. It does not add external reference values, validation tolerances, or final validation outcomes.

Do not treat any Batch 001 case as validated until the reference targets below have been collected, cited, and compared under compatible route, cost, and emissions boundaries.

## 2. Batch-Level Concerns

- All maritime legs used `SeaMatrix haversine fallback`, including the same-port Santos case with `0.0 km sea`.
- Coordinates were not reported by CLI output, so coordinate audit requires a separate source from the cache, database, or a future CLI/export artifact.
- The CLI printed maritime distance in kilometres, not nautical miles. No nautical-mile conversion was added in the Batch 001 results document.
- No external road, maritime, emissions, cost, or service-plausibility references were collected during Batch 001 execution.
- Nearest-port logic requires operational review for some cases, especially where the geometrically nearest port may not be the relevant cabotage service port.
- Cost outputs must be interpreted under the model's energy/operations boundary. They should not be compared directly with full freight rates unless boundary differences are documented.
- All completed cases remain `reference_needed`.

## 3. Case-By-Case Reference Needs

### `TF-VAL-001`: Sao Paulo (SP) -> Santos (SP)

| Item | Batch 001 value or reference need |
| --- | --- |
| Model-selected origin port | `Porto de Santos` |
| Model-selected destination port | `Porto de Santos` |
| Model road-only distance | `77.2 km` |
| Model pre-carriage distance | `86.174 km` |
| Model maritime distance | `0.0 km sea` |
| Model on-carriage distance | `9.031 km` |
| Maritime distance source used by the model | `SeaMatrix haversine fallback`; `haversine_km=0.000`, `coastline_factor=1.000`, `adjusted_km=0.000` |
| Why this case needs reference checking | Close-to-port edge case. The same port was selected for origin and destination, so the validation question is route appropriateness rather than maritime distance magnitude. |
| Road reference needed | Independent road route or manually inspected route for Sao Paulo (SP) -> Santos (SP), plus a check of whether city-centroid routing is acceptable for the thesis boundary. |
| Maritime/corridor reference needed | Evidence that a same-port cabotage leg is not a meaningful maritime corridor for this OD pair, or a documented rule for treating same-port maritime legs as cabotage-inappropriate. |
| Service-plausibility reference needed | Cabotage service or logistics evidence showing that local Sao Paulo to Santos freight should normally be interpreted as road access to port, not a road-sea-road cabotage alternative. |
| Emissions reference needed | Road freight emissions intensity reference for a short loaded truck movement under the same emissions boundary; port-operation emission context only if the edge case remains in comparison tables. |
| Cost-boundary reference needed | Road energy-cost or operating-cost comparator for short road freight if used; avoid full freight-rate comparison unless boundary differences are recorded. |
| Priority | medium |
| Recommended next action | Use this as a route-logic edge case. Collect road reference and document a same-port/cabotage-inappropriate interpretation before changing status. |

### `TF-VAL-002`: Sao Paulo (SP) -> Manaus (AM)

| Item | Batch 001 value or reference need |
| --- | --- |
| Model-selected origin port | `Porto de Santos` |
| Model-selected destination port | `Porto de Manaus` |
| Model road-only distance | `3870.0 km` |
| Model pre-carriage distance | `86.174 km` |
| Model maritime distance | `2744.7 km sea` |
| Model on-carriage distance | `6.763 km` |
| Maritime distance source used by the model | `SeaMatrix haversine fallback`; `haversine_km=2744.683`, `coastline_factor=1.000`, `adjusted_km=2744.683` |
| Why this case needs reference checking | Long road-versus-cabotage case with Northern/Amazon-region complexity. Haversine fallback is not enough to validate a coastal/river corridor. |
| Road reference needed | Independent road routing source or manually inspected route for Sao Paulo (SP) -> Manaus (AM), with notes on ferry, river, or access assumptions if present. |
| Maritime/corridor reference needed | Nautical distance, shipping schedule, port-to-port/corridor reference, ANTAQ-derived observed corridor, or literature for Santos -> Manaus. |
| Service-plausibility reference needed | Evidence that Santos -> Manaus is a plausible cabotage or coastal/river service corridor for the modeled cargo basis. |
| Emissions reference needed | Comparable road truck and cabotage/container-shipping emissions intensity references under matching TTW or WTW boundary notes. |
| Cost-boundary reference needed | Diesel and bunker/energy-cost references, or freight/cabotage cost references only if the non-fuel and port-operation boundaries are explicitly comparable. |
| Priority | high |
| Recommended next action | Collect Santos -> Manaus maritime/corridor distance and service evidence first, then road-distance and emissions/cost intensity references. |

### `TF-VAL-003`: Manaus (AM) -> Fortaleza (CE)

| Item | Batch 001 value or reference need |
| --- | --- |
| Model-selected origin port | `Porto de Manaus` |
| Model-selected destination port | `Porto de Fortaleza` |
| Model road-only distance | `5569.6 km` |
| Model pre-carriage distance | `7.563 km` |
| Model maritime distance | `2391.2 km sea` |
| Model on-carriage distance | `8.656 km` |
| Maritime distance source used by the model | `SeaMatrix haversine fallback`; `haversine_km=2391.151`, `coastline_factor=1.000`, `adjusted_km=2391.151` |
| Why this case needs reference checking | Northern/coastal case from the benchmark context. Manaus-origin routing may require river, coastal, or intermediate-stop interpretation. |
| Road reference needed | Independent road route or manually inspected route for Manaus (AM) -> Fortaleza (CE), with attention to road/ferry/waterway assumptions. |
| Maritime/corridor reference needed | Nautical distance, shipping schedule, observed corridor, or literature reference for Manaus -> Fortaleza or a documented multi-leg equivalent. |
| Service-plausibility reference needed | Evidence of plausible service connection, terminal suitability, or routing pattern between Manaus and Fortaleza for cabotage/container movement. |
| Emissions reference needed | Cabotage emissions intensity or MRV-derived benchmark compatible with a Manaus-origin corridor; road intensity reference for long Northern/Northeastern road movement. |
| Cost-boundary reference needed | Comparable energy or simplified operating-cost references; full freight rates only with explicit boundary mismatch notes. |
| Priority | high |
| Recommended next action | Collect Manaus -> Fortaleza corridor/service evidence before using this case as benchmark support. |

### `TF-VAL-004`: Brasilia (DF) -> Salvador (BA)

| Item | Batch 001 value or reference need |
| --- | --- |
| Model-selected origin port | `Porto de Angra dos Reis` |
| Model-selected destination port | `Porto de Salvador` |
| Model road-only distance | `1472.9 km` |
| Model pre-carriage distance | `1369.936 km` |
| Model maritime distance | `1273.3 km sea` |
| Model on-carriage distance | `5.060 km` |
| Maritime distance source used by the model | `SeaMatrix haversine fallback`; `haversine_km=1273.273`, `coastline_factor=1.000`, `adjusted_km=1273.273` |
| Why this case needs reference checking | Inland-to-coastal case where the selected origin port, `Porto de Angra dos Reis`, may be geometrically nearest but requires operational plausibility review. |
| Road reference needed | Independent road references for Brasilia (DF) -> Salvador (BA) and for the access leg Brasilia (DF) -> Porto de Angra dos Reis. |
| Maritime/corridor reference needed | Nautical distance, corridor, or schedule reference for Porto de Angra dos Reis -> Porto de Salvador if such a cabotage route is operationally relevant. |
| Service-plausibility reference needed | Evidence that Angra dos Reis is an appropriate cabotage/container origin port for this OD case, or evidence supporting an alternate port scenario. |
| Emissions reference needed | Road and multimodal emissions intensity references that can explain the nearly similar road and multimodal emissions result under the model boundary. |
| Cost-boundary reference needed | Cost references under comparable fuel/operations boundary, with special care because the modeled advantage is small and could be sensitive to assumptions. |
| Priority | high |
| Recommended next action | Review port selection first. If Angra dos Reis is not operationally defensible, classify the case as an alternate-port or route-logic limitation before collecting detailed cost references. |

### `TF-VAL-005`: Porto Alegre (RS) -> Recife (PE)

| Item | Batch 001 value or reference need |
| --- | --- |
| Model-selected origin port | `Porto do Rio Grande` |
| Model-selected destination port | `Porto do Recife` |
| Model road-only distance | `3768.6 km` |
| Model pre-carriage distance | `317.409 km` |
| Model maritime distance | `3214.0 km sea` |
| Model on-carriage distance | `1.850 km` |
| Maritime distance source used by the model | `SeaMatrix haversine fallback`; `haversine_km=3213.975`, `coastline_factor=1.000`, `adjusted_km=3213.975` |
| Why this case needs reference checking | Long coastal stress case. The large maritime component drives the model result, so fallback maritime distance must be replaced or bounded with independent evidence. |
| Road reference needed | Independent road routing source or manually inspected route for Porto Alegre (RS) -> Recife (PE), plus access-leg review for Porto Alegre -> Porto do Rio Grande. |
| Maritime/corridor reference needed | Nautical distance, shipping schedule, observed corridor, or literature reference for Porto do Rio Grande -> Porto do Recife. |
| Service-plausibility reference needed | Evidence that Porto do Rio Grande -> Porto do Recife is a plausible cabotage/container corridor, including whether intermediate stops are expected. |
| Emissions reference needed | Long-corridor road and cabotage emissions intensity references under matching cargo, allocation, and emissions-boundary assumptions. |
| Cost-boundary reference needed | Energy/operations cost references or sensitivity inputs for diesel, bunker, port operations, and possible full-rate boundary differences. |
| Priority | high |
| Recommended next action | Collect port-to-port/corridor distance and service-plausibility references before interpreting the large modeled road-to-multimodal difference. |

## 4. Reference Source Targets

Collect source targets without entering values until each reference is saved and cited.

| Reference type | Target sources to collect | Boundary notes to record |
| --- | --- | --- |
| Independent road routing | Another routing provider, manually inspected route, carrier-known distance, DNIT/logistics reference, or benchmark workbook route. | Same OD labels or coordinates, road profile, toll/ferry inclusion, city centroid versus freight terminal/gate interpretation. |
| Maritime distance or corridor | Nautical distance source, shipping schedule, port-to-port/corridor reference, ANTAQ-derived observed corridor, port authority material, shipping line information, or literature. | Direct port-to-port versus intermediate stops, coastal versus river leg treatment, km versus nautical mile units, and whether the source represents operational sailing distance. |
| Cabotage service plausibility | Cabotage schedules, shipping line service maps, port authority information, terminal type evidence, ANTAQ movement evidence, or thesis benchmark assumptions. | Container suitability, regular service availability, river/coastal constraints, nearest-port heuristic limitations, and cases where an alternate port is more defensible. |
| Emissions intensity | Literature or benchmark values for Brazilian heavy trucks, short-sea/cabotage container shipping, MRV-derived indicators, or thesis benchmark workbook values. | TTW versus WTW boundary, cargo allocation method, cargo mass/TEU basis, vessel class, road payload, port operations, and hoteling treatment. |
| Cost boundary | Diesel price source, bunker price source, benchmark workbook values, public freight-rate ranges, or literature separating fuel-only, energy plus port operations, and full freight rates. | BRL date basis, fuel-only versus total freight rate, port tariffs, tolls, driver/labor, inventory, margins, and whether the comparison is order-of-magnitude only. |
| Coordinate audit | Cached place records, geocoder output logs, database cache export, or future CLI output that includes coordinates. | Latitude/longitude, geocoder/provider, cache role, city centroid versus terminal/gate coordinates, and date of retrieval. |

## 5. Update Rules After References Are Collected

Keep `reference_needed` until both model output and independent reference evidence are available for the relevant checks.

Update to `pass_with_limitation` only when:

- road and maritime/corridor distances are plausible under stated tolerances;
- fallback use is documented and either bounded by reference evidence or does not drive a strong conclusion;
- port selection is geographically and operationally defensible;
- emissions and cost comparisons are order-of-magnitude plausible under compatible boundaries;
- remaining caveats are explicit in the validation record.

Update to `fail_boundary_mismatch` when:

- the available reference uses a materially different route, service, cost, or emissions boundary;
- the mismatch prevents direct comparison;
- the model result may still be internally consistent but cannot validate the claimed external quantity.

Update to `fail_operational_plausibility` when:

- the selected port pair or road-sea-road chain is not a plausible freight movement for the case;
- nearest-port logic selects a port that is not service-relevant for the modeled cargo;
- the case should not support main thesis conclusions without an alternate route or port assumption.

Update to `sensitivity_required` when:

- route logic is plausible but the conclusion depends strongly on haversine maritime distance, fuel price, vessel class, allocation mode, port operations, hoteling, access-leg dominance, or uncertain service assumptions;
- independent references provide a range rather than a single defensible value;
- the case remains useful but should be interpreted as conditional rather than validated.

Do not update any case to `pass` until independent references, boundaries, and tolerances have been recorded in the validation evidence.
