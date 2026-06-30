# Validation Plan

## 1. Purpose

This document defines practical validation checks for CabotageLens before the final undergraduate thesis/report is frozen. The goal is to show that model outputs are plausible, internally consistent, and not driven by unrealistic assumptions in distances, emissions, costs, route logic, or edge cases.

This is a validation plan only. It does not report validation results, error statistics, or final acceptance outcomes.

This plan should be read together with the existing TF planning documents: `docs/tf_support/writing/tf_document_structure.md`, `docs/tf_support/methodology/tf_system_boundary.md`, `docs/tf_support/methodology/tf_data_reliability_inventory.md`, and `docs/tf_support/methodology/tf_assumptions_and_approximations.md`.

## 2. Validation principles

Validation checks plausibility, not perfect real-world equivalence. The model is a reproducible comparative estimator, not a reconstruction of every individual truck trip, ship voyage, commercial contract, or terminal operation.

The validation should follow these principles:

- Compare like with like: same origin/destination, cargo mass, TEU basis, route boundary, fuel scope, and cost boundary.
- Keep units explicit: road distance in km, maritime distance in nautical miles or km with conversion shown, fuel in L or kg, emissions in kg CO2e, and intensity in kg CO2e/tkm or g/(t*nm) where relevant.
- Separate direct validation from sensitivity analysis. Validation asks whether a baseline result is plausible; sensitivity asks whether conclusions survive reasonable changes in assumptions.
- Prefer observed or concrete references over assumptions. Use API/reference distances, published port-to-port distances, known schedules, benchmark workbook values, literature ranges, or manually inspected routes.
- Do not force exact matches when boundaries differ. If a reference includes tolls, inventory cost, terminal tariffs, well-to-wake emissions, or full freight rates, mark the boundary difference before comparing.
- Record failure reasons. A failed check can reveal wrong data, a valid limitation, an inappropriate route, or a need for sensitivity analysis.
- Treat Northern and Amazon-region routes carefully because road access, waterways, ferry segments, and operational feasibility can differ from simple road-plus-coastal-cabotage assumptions.

## 3. Validation check matrix

| Check | Purpose | Method | Data needed | Acceptance criterion | If it fails |
| --- | --- | --- | --- | --- | --- |
| Road distance validation | Confirm that ORS/API road distances are plausible for direct road, first mile, and last mile legs. | Select a small OD sample. For each road leg, compare the model/API distance against at least one independent reference such as another routing provider, manually inspected route, known carrier distance, DNIT/logistics reference, or benchmark workbook route. Record origin/destination coordinates and provider profile. | Model road distance in km; resolved origin/destination coordinates; independent reference distance in km; route notes for tolls, ferries, or inaccessible segments. | Distances should be directionally consistent and within a pre-declared tolerance for the thesis, such as narrower tolerance for simple highway routes and wider tolerance for Amazon, ferry, or ambiguous urban access routes. Large deviations must have an explained route-boundary cause. | Check geocoding first. If geocoding is wrong, correct the input or cache. If provider routing differs but is defensible, mark as limitation. If the route is operationally implausible, exclude it from main conclusions or use a documented alternate route assumption. |
| Maritime distance validation | Confirm that port-to-port sea distances are plausible and that fallback distances do not distort conclusions. | For selected port pairs, compare `sea_matrix` or directional/corridor distances against published port-to-port distances, cabotage schedules, nautical references, shipping line route information, ANTAQ-derived corridors, or literature values. Separate direct matrix distances from haversine/coastline-factor fallback. | Model maritime distance in km and nm; distance source flag; port coordinates; reference distance or schedule path; notes on river, coastal, or intermediate-stop routing. | Matrix or observed/corridor distances should be close enough to accepted nautical references for thesis use. Fallback distances are acceptable only when explicitly labeled and not used to support strong conclusions without sensitivity analysis. | Correct data if a matrix value is clearly wrong. If the route requires intermediate ports or inland waterways, validate as a corridor rather than a direct line. If no reliable reference exists, downgrade confidence and require sensitivity analysis. |
| Emissions order-of-magnitude validation | Check whether road and cabotage emissions intensities are compatible with literature or benchmark ranges. | Convert model outputs into comparable intensities: kg CO2e/km, kg CO2e/t, kg CO2e/tkm for road legs, and kg CO2e/t, kg CO2e/tkm or g CO2e/(t*nm) for maritime legs. Compare against literature ranges, benchmark workbook values, MRV-derived indicators, and published road/cabotage references. | Model emissions, fuel use, cargo mass, distance, transport work, fuel type, emission factor, and reference intensity ranges with matching boundary notes. | Values should fall within a plausible order of magnitude for the stated vehicle, vessel, cargo, and tank-to-wheel boundary. Outliers must be explained by distance, payload, fallback path, port operations, or data coverage. | Audit units and conversion factors first. Check kg vs tonnes, km vs nm, per-shipment vs per-tonne allocation, and double counting of hoteling. If still high or low, mark as limitation, exclude from headline results, or run sensitivity analysis. |
| Cost order-of-magnitude validation | Check whether modeled cost outputs are plausible under the stated cost boundary. | Compare energy-cost outputs against public freight-rate references, benchmark workbook values, literature ranges, or known industry ranges. Keep separate comparisons for fuel-only cost, energy plus port operations, and full freight-rate references. | Model costs in BRL; diesel price in BRL/L; bunker price in BRL/mt; port-ops cost where included; cargo mass/TEU; reference freight or cost values; boundary notes. | Fuel-only results should be plausible as energy costs, not necessarily close to full freight rates. When compared with full freight references, the model should be lower unless non-fuel costs are added. | If fuel cost is implausible, check fuel price source, unit conversion, fuel quantity, and route distance. If only full freight references differ, state boundary mismatch and avoid claiming full cost validation. Add sensitivity or non-fuel cost scenarios before economic conclusions. |
| Route logic validation | Check whether selected ports and multimodal chains are geographically and operationally plausible. | Inspect selected origin port, destination port, first mile, sea leg, and last mile for a sample of OD pairs. Include nearest-port edge cases, OD pairs near ports, OD pairs far from ports, and Northern/Amazon-region cases. Compare selected ports against known cabotage service availability or benchmark assumptions where available. | Resolved coordinates; selected ports; first-mile and last-mile distances; sea distance/source; known service or schedule evidence; port feasibility notes. | The chain should be geographically coherent and commercially plausible enough for the thesis case. Nearest-port choices must not be treated as operationally valid when service, frequency, or waterway constraints contradict them. | If the route is not operationally plausible, mark it invalid for main conclusions, manually define a documented alternate port pair for sensitivity, or classify it as future work requiring service-network modeling. |
| Nearest-port edge case check | Detect cases where the nearest port is not the feasible cabotage port. | For selected OD pairs, compare nearest-port output with at least one alternative port used in practice or in references. Inspect whether a small distance advantage is outweighed by service feasibility. | Candidate ports, access distances, known cabotage service/schedule notes, terminal type, and route availability. | Nearest-port selection is acceptable only when it is also operationally plausible or clearly labeled as a geometric heuristic. | Downgrade conclusion confidence, use alternate port scenario, or exclude the OD pair from headline claims. |
| OD pairs close to ports | Check whether the model behaves sensibly when origin or destination is already near a port. | Use OD pairs within the port city/metro area and inspect whether first-mile or last-mile distances are near zero but not negative, and whether cabotage is not forced for very short local movements. | Port-city OD inputs, selected ports, road-only distance, first/last mile distance, sea leg if applicable. | Local access distances should be non-negative and reasonable. Very short OD pairs should normally favor road-only or be flagged as inappropriate for cabotage. | Check geocoding and port gate coordinates. If cabotage is selected for a clearly local movement, mark as inappropriate route logic for thesis conclusions. |
| OD pairs far from ports | Check whether long pre-carriage or on-carriage legs make the multimodal chain implausible or weak. | Select inland OD pairs far from coastal ports and inspect the share of total distance occurring by road access legs. | OD coordinates, selected ports, first-mile/last-mile distances, road-only distance, total multimodal distance. | Multimodal results are acceptable only if the thesis interprets them as generated alternatives, not guaranteed feasible services. Excessive road access should be highlighted. | Mark as limitation, require sensitivity, or exclude from main cabotage-favorable conclusions if access legs dominate. |
| Northern/Amazon-region route logic | Check whether road, river, and cabotage assumptions are valid in areas with complex access. | Include at least one Amazon/Northern OD pair and inspect whether the API road route, selected ports, and sea/waterway leg reflect plausible logistics. | Road route reference, ferry/waterway notes, selected ports, known cabotage or river service evidence, manual inspection. | The route must not silently treat unavailable road/waterway combinations as ordinary highway or coastal legs. | If access is complex or unsupported, mark the case as special, exclude from general validation, or create a separate limitation/future-work item for inland waterway modeling. |
| Extreme short-distance check | Confirm behavior for very short OD pairs where cabotage should usually be inappropriate. | Select same-city or nearby-city OD pairs and inspect direct road distance, selected ports, and total multimodal distance. | Model outputs and route map/reference inspection. | The model should not support a strong cabotage conclusion for very short local routes unless there is a special operational reason. | Exclude from modal-shift conclusions or add a rule/limitation that short OD pairs are outside the intended use case. |
| Extreme long-distance check | Confirm behavior for national-scale OD pairs where route distance, emissions, and costs can become large. | Select long corridors and inspect whether distances, fuel, emissions, and costs scale monotonically and remain plausible. | Long OD outputs, reference road/maritime distances, emissions intensities, cost inputs. | No negative, zero, or discontinuous values; intensities should remain plausible; route source and fallback status must be visible. | Audit unit conversions and fallbacks. If the result is plausible but uncertain, require sensitivity analysis. |
| Complex inland/waterway leg check | Detect OD pairs requiring ferry, river, or non-standard access not represented by the current road-cabotage-road abstraction. | Identify routes where inland waterways or ferry crossings are likely. Inspect provider route geometry and compare with known logistics patterns. | Manual route notes, provider route, port selections, waterway references if available. | Such routes should be labeled as special cases unless the abstraction is clearly valid. | Exclude from main sample, mark as methodology debt, or define a separate waterway modeling extension. |
| Cabotage-inappropriate route check | Prevent overinterpreting routes where cabotage is not a meaningful alternative. | Identify short, inland-inland, same-state, or poorly served OD pairs and flag them before conclusions. | OD sample, selected ports, access-leg share, known service evidence. | The thesis should not claim cabotage advantage for routes where the constructed chain is operationally artificial. | Exclude, downgrade confidence, or present only as a stress test of the model rather than a candidate modal-shift corridor. |
| Reproducibility and output audit check | Confirm that validation cases can be rerun and audited. | For each validation case, record code version, input payload, resolved coordinates, selected ports, route cache status, data artifact paths, fuel price source, and calculation boundary. | Run metadata, input JSON, output JSON, cache/source flags, artifact paths, and date. | Every validation result used in the thesis should be traceable to inputs and artifacts. | Re-run with complete metadata or omit the case from formal validation evidence. |

## 4. Suggested validation sample

The sample should be small enough to inspect manually and broad enough to exercise the model's major assumptions. The following candidates are proposed for validation planning only; the validation should not be considered complete until independent references are collected and the checks are run.

### OD pairs

| Candidate OD pair | Why include it | Main checks |
| --- | --- | --- |
| Sao Paulo (SP) -> Santos (SP) | Origin close to a major port; cabotage should usually be inappropriate for local movement. | Road distance, close-to-port behavior, cabotage-inappropriate route check. |
| Sao Paulo (SP) -> Manaus (AM) | Long corridor with strong road-vs-cabotage relevance and Amazon-region complexity. | Road distance, maritime distance, route logic, emissions order of magnitude, Northern/Amazon special handling. |
| Manaus (AM) -> Fortaleza (CE) | Appears in the thesis benchmark context and exercises Northern/coastal routing. | Benchmark comparison, maritime route plausibility, emissions order of magnitude, port selection. |
| Recife (PE) -> Fortaleza (CE) | Coastal regional OD where cabotage may be plausible but road competition is also relevant. | Maritime distance, road distance, short/medium corridor interpretation. |
| Brasilia (DF) -> Salvador (BA) | Inland origin to coastal destination with meaningful access-leg effects. | Far-from-port route logic, nearest-port selection, road access share. |
| Goiania (GO) -> Belem (PA) | Inland/Northern-oriented route that may reveal road network or port-selection limitations. | Road distance, port feasibility, long-distance edge case. |
| Porto Alegre (RS) -> Recife (PE) | Long coastal corridor with a large maritime component. | Maritime distance, emissions order of magnitude, fuel/cost sensitivity. |
| Rio de Janeiro (RJ) -> Vitoria (ES) | Coastal short-to-medium route where nearest-port and service assumptions should be inspected. | Maritime distance, route logic, cabotage appropriateness. |

### Port pairs

| Candidate port pair | Why include it | Main checks |
| --- | --- | --- |
| Santos (SP) -> Manaus (AM) | Long corridor with river/Northern implications. | Maritime distance, corridor logic, observed-route coverage. |
| Santos (SP) -> Suape (PE) | Major Brazilian cabotage corridor candidate. | Maritime distance, emissions intensity, cost plausibility. |
| Santos (SP) -> Rio de Janeiro (RJ) | Short coastal pair where distance approximation can be inspected. | Maritime distance, short-route plausibility. |
| Suape (PE) -> Fortaleza (CE) | Regional coastal pair with possible schedule/reference availability. | Maritime distance and route logic. |
| Itajai/Navegantes (SC) -> Santos (SP) | Southern container corridor candidate. | Maritime distance and port selection. |
| Belem/Vila do Conde (PA) -> Manaus (AM) | Northern/Amazon-region waterway-sensitive pair. | Complex inland/waterway handling and distance source. |

### Reference sources to collect before running validation

- Independent road distances from another routing provider, manually inspected route maps, carrier-known distances, DNIT/logistics references, or benchmark workbook values.
- Port-to-port distances from nautical references, shipping schedules, port authority material, shipping line route information, literature, or ANTAQ-derived observed corridors.
- Emissions intensity references for Brazilian heavy trucks, short-sea/cabotage container shipping, MRV-based container ship indicators, and the Gustavo Costa workbook where boundaries match.
- Cost references for diesel price, bunker price, public freight-rate ranges, benchmark workbook costs, and literature that separates fuel cost from total freight rate.
- Service plausibility references such as cabotage schedules, port pair availability, terminal type, and known operational constraints.

## 5. Failure handling

Failed validation should be treated explicitly in the thesis. It should not be hidden or averaged away.

- Correct the data if the failure is a clear data error, such as wrong coordinates, wrong port label, wrong distance entry, or unit conversion mistake.
- Mark as limitation if the failure comes from a known model boundary, such as API routing instead of GPS traces, fuel-only cost instead of freight rate, or tank-to-wheel emissions instead of well-to-wake emissions.
- Exclude invalid routes from headline conclusions when the selected port chain is not operationally plausible or the OD pair is outside the intended use case.
- Downgrade conclusion confidence when a case is plausible but relies on fallback distances, fallback vessel class intensity, missing MRV coverage, or uncertain service availability.
- Require sensitivity analysis when the route is plausible but conclusions depend strongly on fuel price, truck km/L, maritime intensity, empty backhaul, hoteling, port operations, or non-fuel cost assumptions.
- Preserve the failure as evidence when it reveals an important methodology debt, such as missing service-network logic or missing inland waterway representation.

## 6. Methodology debts

- Build a validation case log that records input payloads, resolved coordinates, selected ports, distance sources, cache status, fuel prices, emission factors, and data artifact versions.
- Collect independent road-distance references for the final thesis OD sample.
- Collect independent maritime distance references for the final port-pair sample.
- Define a pre-declared tolerance policy for road and maritime distance comparisons before running validation.
- Compile literature or benchmark ranges for road and cabotage emissions intensity under the same tank-to-wheel boundary.
- Compile cost references that separate fuel-only, energy-plus-port-ops, and full freight-rate boundaries.
- Add a route-plausibility review sheet covering nearest-port edge cases, close-to-port cases, far-from-port cases, and Northern/Amazon-region cases.
- Decide in advance which failed routes will be corrected, excluded, treated as sensitivity cases, or retained only as limitations.
- Ensure the final thesis tables show whether a maritime result used observed route intensity, corridor aggregation, class fallback, or another fallback.

## 7. Recommended thesis wording

The following wording can be adapted for the validation or methodology chapter.

> The validation procedure is designed to test plausibility and methodological consistency rather than exact equivalence with every real-world shipment. Differences are expected where reference sources use different route choices, commercial boundaries, fuel scopes, or operational assumptions.

> Road distances are checked against independent route references for a small sample of origin-destination pairs. The objective is to identify geocoding errors, route-provider anomalies, and cases where the modeled route is not representative of a plausible freight movement.

> Maritime distances are checked against external port-to-port references or observed route evidence where available. Results that depend on fallback distance approximations are treated with lower confidence and are not used alone to support strong conclusions.

> Emissions validation is performed at order-of-magnitude level using comparable intensity metrics, such as kg CO2e per tonne-kilometre or fuel/emissions per tonne-nautical mile. The comparison is restricted to the tank-to-wheel boundary unless upstream fuel-cycle factors are explicitly added.

> Cost validation is interpreted according to the model boundary. Fuel and simplified operational costs are not expected to match full freight rates unless tolls, labor, port tariffs, inventory cost, service frequency, and commercial margins are included.

> When a validation check fails, the case is not automatically discarded. The failure is classified as a data issue, model-boundary limitation, operational infeasibility, or sensitivity-analysis requirement, and the final conclusion confidence is adjusted accordingly.
