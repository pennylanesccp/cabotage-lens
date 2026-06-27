# TF Literature Audit Implementation Plan

This document translates the merged literature audit in `docs/literature_audit/` into an incremental implementation plan for CabotageLens. It is an impact audit and prioritization document, not a blanket instruction to change model factors.

## 1. Source audit snapshot

The literature audit added review matrices, claim/source mapping, model intersections, citation gaps, PDF diagnostics, and paper notes. The audit explicitly states that its recommendations have not been applied to code or main documentation yet.

Reviewed or partially reviewed sources currently support four main methodological themes:

- Brazilian cabotage context and decarbonization potential (`icct2022`).
- Brazilian multimodal competitiveness and supernetwork comparison (`competitiveness2024`).
- Fuel pathway and CO2e / WTW boundary discussion (`decarb2024`).
- Short-sea / modal-shift caution that maritime transport is not automatically better in every corridor (`shortsea2019`, `modalshiftreview2020`).

The hoteling and port-operation papers (`berth2009`, `shipops2022`, `berthairquality2010`) and the iso-emission visualization paper (`isoemission2019`) remain pending or incomplete and should not be used to overwrite model parameters without a new audit pass.

## 2. Findings that require code or UI changes

| Finding | Why it affects implementation | Priority | Implementation direction |
| --- | --- | --- | --- |
| UI/result labels must distinguish CO2 vs CO2e. | Generic "Emissions" labels can be interpreted as CO2-only or CO2e. The current fuel helper returns `co2e_kg`, so outputs should say CO2e when that is the displayed metric. | High | Rename UI labels and exported/result descriptions to `TTW CO2e` or equivalent where the model boundary is operational TTW. |
| UI/docs must distinguish TTW vs WTW/LCA. | Several audited papers report WTW or LCA values that cannot be directly compared with operational TTW model outputs. | High | Add UI captions/tooltips and methodology notes stating that current app results are operational TTW unless explicitly noted. |
| Costs must not be presented as commercial freight rates. | The current model primarily estimates fuel/operational proxies, not full commercial freight with margins, tariffs, inventory time, insurance, demurrage, service frequency, and reliability. | High | Use labels such as `cost estimate`, `operational estimate`, or `model cost proxy`; avoid `freight rate` wording unless a future module actually models it. |
| Maritime distance fallback needs override/bounds support for Batch 001B. | Batch 001 found haversine fallback can materially understate sea distance, biasing maritime emissions/costs. | High | Implement distance source provenance, external override fields, and conservative bounds before reclassifying affected validation cases. |
| Same-port and cabotage-inappropriate cases need explicit warnings. | Same-port maritime legs or ports without plausible container cabotage service should not be treated as valid cabotage alternatives. | High | Add route construction validation or result warnings for same-port, zero-sea-distance, and service-plausibility failures. |
| Validation outputs must preserve fallback/override provenance. | Future thesis validation needs to show whether each distance/result came from SeaMatrix, haversine fallback, external reference, manual override, or sensitivity bound. | High | Add metadata columns/fields for distance source, override source, fallback flag, and confidence classification in Batch 001B outputs. |

## 3. Findings that require documentation changes only

| Finding | Documentation action | Priority |
| --- | --- | --- |
| CabotageLens is a route-comparison estimator, not a full commercial logistics optimization model. | State in system boundary, assumptions, and discussion sections. | High |
| Nearest-port logic is a simplification compared with supernetwork methods. | Explain that the model is lighter than `competitiveness2024` and may approximate an upper-bound or feasibility screen rather than actual service availability. | High |
| Door-to-door comparison is methodologically correct and should be emphasized. | Use the audit to justify first-mile + sea + last-mile comparisons instead of ship-only versus truck-only comparisons. | Medium |
| Route-specific results are necessary because cabotage is not universally better. | Add caution to results/discussion: corridor distance, access legs, utilization, vessel class, service plausibility, and port operations can reverse the modal ranking. | Medium |
| Port hoteling and terminal operations matter, but are sensitive to boundary and double-counting. | Document when hoteling is included, when it is skipped, and why. | Medium |
| Validation and sensitivity are required before strong thesis claims. | Tie Batch 001B and sensitivity outputs to final claims. | Medium |

## 4. Findings for limitations or future work

| Finding | Recommended treatment |
| --- | --- |
| Full WTW/LCA emissions modeling. | Future work unless a separate boundary-change issue is opened with defensible factors and sensitivity tests. |
| Alternative fuels such as HVO with WTW CO2e factors. | Future work or scenario module only; do not mix into current TTW baseline. |
| Real multimodal supernetwork with service frequency, sailing schedules, port calls, inventory time, and terminal availability. | Future work; cite `competitiveness2024` as a higher-fidelity benchmark. |
| Integration with commercial cabotage schedules and freight rates. | Future work; current app should stay as operational/methodological estimator. |
| Complete Brazilian port dwell time and terminal-efficiency dataset. | Future work or data-acquisition task. |
| Iso-emission maps / breakeven visualization. | Future work after distance and boundary provenance are stable. |

## 5. Findings not to implement now

- Do not replace current TTW factors with WTW factors from `competitiveness2024` or `decarb2024`.
- Do not introduce HVO, MDO, VLSFO, biodiesel, shore power, or LCA scenarios as default behavior in this pass.
- Do not rewrite Batch 001 historical validation results.
- Do not implement a full supernetwork model in this small literature-audit follow-up.
- Do not add new numerical factors from pending hoteling papers until `berth2009`, `shipops2022`, and `berthairquality2010` are fully reviewed.
- Do not claim cost competitiveness using commercial freight-rate language unless the missing commercial components are modeled or explicitly bounded.

## 6. Values that can be used as direct references

These values can support context, benchmarking, or future sensitivity discussions, provided the boundary is preserved exactly.

| Source key | Value | Boundary / unit | Safe use |
| --- | --- | --- | --- |
| `icct2022` | Cabotage: 8 gCO2/TKU; road: 52 gCO2/TKU. | CO2 / tonne-kilometer, operational/tailpipe context as audited. | Macro Brazilian context and plausibility comparison, not direct model replacement without matching boundary. |
| `icct2022` | 4.7 MtCO2e cabotage sector emissions in 2020. | Sector-level CO2e. | National context and motivation. |
| `icct2022` | Road freight rates around 20% higher than cabotage on average. | Literature context, commercial/economic statement. | Discussion only unless the model adds comparable commercial freight-rate components. |
| `competitiveness2024` | Cabotage competitiveness threshold above 1,800 km. | Study-specific network/cost/CO2e setup. | Benchmark for discussion and route-result interpretation, not a hard app rule. |
| `competitiveness2024` | 15% EBIT road transportation margin. | Study-specific commercial/cost modeling assumption. | Reference for future cost-boundary sensitivity, not current default unless implemented explicitly. |
| `decarb2024` | 3.5 t/day vessel fuel consumption during voyage; 5.0 t/day in port. | Study-specific cabotage fuel consumption context. | Sanity check and sensitivity candidate after boundary review. |
| `decarb2024` | HVO WTW factor of 23.7 gCO2e/MJ and 75.4% potential reduction in the studied scenario. | WTW / CO2e. | Alternative-fuel future work or scenario discussion only. |
| `shortsea2019` | Feeder emissions values reported in gCO2/TEU-km for European cases. | CO2 / TEU-km; Europe-specific. | Qualitative support for utilization/corridor sensitivity, not direct Brazilian calibration. |

## 7. Values not usable directly without boundary conversion or validation

| Value category | Why it cannot be directly substituted |
| --- | --- |
| WTW gCO2eq/MJ factors from `competitiveness2024`. | Current app emissions are operational TTW factors by fuel mass in parts of the model. WTW energy-basis factors require fuel energy content, lifecycle boundary alignment, and revised output labeling. |
| HVO WTW factor and HVO reduction scenario from `decarb2024`. | HVO is a lifecycle alternative-fuel scenario, not a drop-in replacement for current TTW VLSFO/MDO baseline. |
| 3.5 t/day voyage and 5.0 t/day port fuel consumption from `decarb2024`. | These are schedule/model averages from a specific study; using them requires checking vessel class, allocation method, port time separation, and whether transport-work intensities already include port fuel. |
| `shortsea2019` European feeder CO2 intensities. | Different geography, vessel utilization, service design, cargo allocation, and CO2/CO2e boundary. |
| Commercial freight-rate or EBIT assumptions. | Current cost model is not a complete commercial freight-rate model. Margins, tariffs, inventory cost, service frequency, demurrage, labor, insurance, and overhead are not fully included. |
| Pending hoteling/air-quality paper values. | The audit marks these papers pending; values should be extracted and checked before any implementation. |

## 8. Methodological risks if boundaries are mixed

- Mixing CO2 and CO2e can overstate or understate climate impact depending on whether CH4, N2O, black carbon, or other gases are included.
- Mixing TTW and WTW can make one mode appear cleaner simply because upstream fuel production is included for one mode but excluded for the other.
- Converting gCO2eq/MJ to kgCO2e/kg fuel requires energy content assumptions; using the wrong lower heating value or fuel density can create hidden unit errors.
- Adding hoteling emissions on top of a transport-work intensity that already embeds annual operational fuel can double-count port fuel.
- Treating fuel/operational cost as commercial freight rate can produce invalid economic conclusions about cabotage competitiveness.
- Using haversine sea distances as if they were navigable or service distances can systematically bias results in favor of cabotage on coastal/river corridors.

## 9. Relationship to Batch 001B validation

Batch 001 is a historical validation record and should remain unchanged. The literature audit should inform Batch 001B in four ways:

1. **Distance provenance**: every maritime distance should preserve source metadata (`SeaMatrix`, `haversine fallback`, external reference, manual override, or sensitivity bound).
2. **Fallback correction**: corridors affected by haversine fallback should receive external reference distances, conservative bounds, or sensitivity bands before thesis-grade interpretation.
3. **Cabotage appropriateness**: same-port cases, zero-sea-distance cases, and ports without plausible container cabotage service should be classified or warned explicitly.
4. **Boundary interpretation**: validation tables should identify whether emissions are TTW CO2e, WTW CO2e, CO2-only, or boundary-only references. Literature values should be used as plausibility checks only when boundaries match.

Batch 001B should therefore be treated as the implementation track for route-distance overrides, same-port warnings, service-plausibility flags, and provenance-preserving validation outputs.

## 10. Incremental implementation priorities

### High priority

1. Standardize visible labels and docs around `TTW CO2e` versus CO2/WTW/LCA.
2. Standardize cost language as `cost estimate` or `operational proxy`, not full freight quote.
3. Plan and implement maritime distance override/bounds support for Batch 001B.
4. Add same-port and cabotage-inappropriate warnings/classifications.
5. Preserve distance/fallback/override provenance in validation outputs.

### Medium priority

1. Improve methodology docs using the audit.
2. Add UI disclaimers/tooltips about emissions boundary and cost boundary.
3. Review hoteling model against `decarb2024`, but do not auto-replace factors.
4. Prepare sensitivity structure for load factor, maritime distance, maritime fuel consumption, hoteling time, and cost inputs.

### Low priority / future work

1. Full WTW/LCA modeling.
2. Real multimodal supernetwork with frequency and commercial service availability.
3. Integration with shipping schedules and commercial pricing.
4. Complete port dwell time / terminal efficiency data acquisition.
5. Iso-emission map visualization.

## 11. Changes allowed in the current small pass

This pass may safely include:

- Restoring `GEMINI.md` to general main-branch guidance.
- Creating this implementation plan.
- Adding documentation-only boundary clarifications.
- Adding small UI wording/caption changes for TTW CO2e and cost-boundary interpretation.

This pass should not include:

- Numerical factor replacement.
- Major model refactoring.
- Validation result rewrites.
- New committed PDFs, workbooks, references folders, secrets, or caches.
