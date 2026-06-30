# Model Intersections

This document explains how the literature intersects with the current CabotageLens model, organized by theme.

## 1. Brazilian freight and cabotage context
* **What literature says**: Brazilian freight is heavily reliant on road transport, but cabotage presents a significant opportunity for growth and decarbonization (`icct2022`).
* **What CabotageLens does**: Models road-only vs road-cabotage-road to demonstrate the potential of this modal shift.
* **Alignment**: High. The core premise of the app aligns with national transportation research.
* **Mismatch/Limitation**: CabotageLens focuses on theoretical route capability, not regulatory or market barriers to entry.
* **Recommended Thesis Wording**: Emphasize cabotage as a decarbonization opportunity while acknowledging market barriers are outside the system boundary.
* **Methodology Update**: None. (Writing-only change).

## 2. Modal shift and short sea shipping competitiveness
* **What literature says**: Modal shift requires competitive door-to-door performance, not just efficient sea legs (`modalshiftreview2020`).
* **What CabotageLens does**: Implements a full door-to-door calculation including first-mile and last-mile road legs.
* **Alignment**: High.
* **Mismatch/Limitation**: CabotageLens doesn't model the full time delay of port processing (only emissions/cost impact).
* **Recommended Thesis Wording**: Clearly state that competitiveness in CabotageLens is based on cost and emissions, and service time is excluded from the primary fitness function.
* **Methodology Update**: Ensure time-in-transit limitations are stated. (Writing-only change).

## 3. Brazilian cabotage competitiveness and supernetwork studies
* **What literature says**: Advanced studies use multimodal supernetworks to assess competitiveness comprehensively (`competitiveness2024`).
* **What CabotageLens does**: Uses a simplified point-to-point routing logic with nearest-port assumptions.
* **Alignment**: Partial. The goal is similar, but CabotageLens uses a lighter architectural approach.
* **Mismatch/Limitation**: A supernetwork models actual service availability and frequencies; CabotageLens assumes generic availability.
* **Recommended Thesis Wording**: Contrast the nearest-port heuristic with supernetwork approaches, noting the heuristic provides a theoretical upper-bound of competitiveness.
* **Methodology Update**: Explicitly document the nearest-port assumption vs supernetwork capability. (Writing-only change).

## 4. Road-only versus road-cabotage-road comparison
* **What literature says**: Direct door-to-door comparison is the standard for evaluating environmental friendliness (`shortsea2019`, `isoemission2019`).
* **What CabotageLens does**: Directly compares road-only routing with multimodal routing.
* **Alignment**: High.
* **Mismatch/Limitation**: None.
* **Recommended Thesis Wording**: Cite these papers to justify the tool's core structural design.
* **Methodology Update**: None.

## 5. Route construction and nearest-port selection
* **What literature says**: Port access and distance significantly influence viability (`sssfactors2018`).
* **What CabotageLens does**: Selects nearest ports based on geographical proximity, with some alternate port logic.
* **Alignment**: Moderate.
* **Mismatch/Limitation**: Nearest port may not have a commercial service connecting to the destination's nearest port.
* **Recommended Thesis Wording**: Highlight the "same-port" and "unserved pair" edge cases as identified in validation.
* **Methodology Update**: The correction plan for Batch 001 already addresses same-port cases; ensure this is implemented in code eventually. (Requires code change).

## 6. Maritime distance and service plausibility
* **What literature says**: Accurate maritime distance is essential for correct emissions estimates, and cabotage costs generally beat road over 1,800km (`competitiveness2024`).
* **What CabotageLens does**: Uses SeaMatrix for distance, with a haversine fallback.
* **Alignment**: Moderate (due to fallback).
* **Mismatch/Limitation**: Validation found haversine fallback severely underestimates true maritime distance.
* **Recommended Thesis Wording**: Acknowledge the haversine limitation and its impact on sensitivity.
* **Methodology Update**: Implement distance correction/bounding for the haversine fallback. (Requires code change).

## 7. Emissions boundary and fuel factors
* **What literature says**: Fuel choices (MDO, VLSFO) drastically alter the footprint (`decarb2024`).
* **What CabotageLens does**: Models specific emissions factors for vessels and trucks.
* **Alignment**: High.
* **Mismatch/Limitation**: The app must be careful not to hardcode a single fuel without allowing for scenario variations if competing with advanced fuel studies.
* **Recommended Thesis Wording**: Define the baseline fuel assumption clearly.
* **Methodology Update**: Verify current emissions factors against `decarb2024`. (Model check).

## 8. CO2 versus CO2e
* **What literature says**: They must not be mixed; CO2e includes methane and other GHGs (`decarb2024`, `icct2022`).
* **What CabotageLens does**: Tracks emissions.
* **Alignment**: High, pending terminology audit.
* **Mismatch/Limitation**: If CabotageLens outputs "Emissions" generically, it risks conflation.
* **Recommended Thesis Wording**: Explicitly specify whether the output is CO2 or CO2e throughout the UI and documentation.
* **Methodology Update**: Audit all UI labels and docs to ensure gas species is specified. (Requires code/UI change).

## 9. TTW versus WTW versus LCA
* **What literature says**: Scope of emissions must be explicit (`maritimelca2024`).
* **What CabotageLens does**: Primarily focuses on operational (TTW) emissions.
* **Alignment**: High, as long as it's stated.
* **Mismatch/Limitation**: Misinterpretation by users comparing WTW road to TTW shipping.
* **Recommended Thesis Wording**: "This tool bounds its emissions analysis to Tank-to-Wake (TTW)..."
* **Methodology Update**: Update `docs/tf_support/methodology/tf_system_boundary.md` to ensure TTW is explicitly declared as the primary boundary. (Writing-only change).

## 10. Port operations and hoteling
* **What literature says**: Hoteling and port equipment contribute materially to the total footprint (`berth2009`, `shipops2022`, `decarb2024`). Average daily port fuel consumption is around 5.0 tons/day (`decarb2024`).
* **What CabotageLens does**: Includes a port ops and hoteling model.
* **Alignment**: High.
* **Mismatch/Limitation**: Risk of double-counting if voyage time includes hoteling time.
* **Recommended Thesis Wording**: Detail how hoteling time is separated from steaming time.
* **Methodology Update**: Cite `berth2009` and `shipops2022` in `docs/hoteling_model.md`. (Writing-only change).

## 11. Cost boundary and freight-rate limitations
* **What literature says**: Commercial freight rates include margins, risk, and overhead, unlike pure operational costs (`competitiveness2024`).
* **What CabotageLens does**: Estimates cost as an indicator, not a commercial quote.
* **Alignment**: High, provided the limitation is clear.
* **Mismatch/Limitation**: Users might mistake output for a freight quote.
* **Recommended Thesis Wording**: "Cost outputs represent operational estimates and should not be presented as full commercial freight rates."
* **Methodology Update**: Add UI tooltips/disclaimers. (Requires UI change).

## 12. Validation and sensitivity
* **What literature says**: Sensitivity analysis is necessary before drawing broad modal-shift conclusions (`modalshiftreview2020`).
* **What CabotageLens does**: Includes a validation plan and sensitivity analysis framework.
* **Alignment**: High.
* **Mismatch/Limitation**: None.
* **Recommended Thesis Wording**: N/A.
* **Methodology Update**: Execute the sensitivity plan as designed.
