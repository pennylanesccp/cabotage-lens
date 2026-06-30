# System Boundary and Functional Unit

This document defines the system boundary, functional unit, and the scope of the compared transport chains for the final academic report (Trabalho de Formatura - TF). The goal is to provide a defensible, transparent methodology for comparing freight transport alternatives in Brazil, specifically focusing on road-only and multimodal (road-cabotage-road) transport.

## 1. Functional Unit

The functional unit is the reference basis for quantifying the inputs and outputs of the compared transport systems.

**Defined Functional Unit:**
The transportation of a specified mass of containerized cargo (in tonnes or TEUs) between a defined origin and destination pair within Brazil.

**Expression of Results:**
Results will be expressed in terms of:
- Total operational TTW CO2e and model cost estimates **per shipment** (for a direct scenario comparison).
- Specific operational TTW CO2e and model cost estimates **per tonne** or **per TEU** (to normalize across different cargo volumes).
- Intensity metrics **per tonne-kilometer (t-km)** (to allow comparability across different origin-destination pairs and distances).

**Rationale for the Final Thesis:**
Using a shipment-based functional unit normalized to tonnes and tonne-kilometers is standard practice in freight transport studies. It provides a concrete basis for comparing the absolute environmental and economic performance of specific logistics corridors, while the normalized metrics (per t-km) allow for broader benchmarking against other literature and transport modes.

## 2. Compared Transport Chains

The study evaluates two primary transport profiles to deliver the functional unit:

### 2.1 Road-Only Transport Chain
This chain relies entirely on heavy-duty truck transport from origin to destination.

**Included Legs:**
- Direct road haulage from the origin facility to the destination facility.

### 2.2 Multimodal Transport Chain (Road-Cabotage-Road)
This chain uses coastal shipping (cabotage) for the primary long-haul segment, supported by road transport for the initial and final miles.

**Included Legs:**
- **Origin Drayage (Road):** Truck transport from the origin facility to the port of origin.
- **Port Operations (Origin):** Port-side handling and berth-side hoteling/auxiliary fuel or emissions associated with loading when the selected model boundary supports separate inclusion, with source provenance retained for observed, estimated, documented-default, zero-activity, or unavailable values.
- **Maritime Sailing (Cabotage):** Coastal shipping from the port of origin to the port of destination.
- **Port Operations (Destination):** Port-side handling and berth-side hoteling/auxiliary fuel or emissions associated with unloading when the selected model boundary supports separate inclusion, with the same source-provenance hierarchy.
- **Destination Drayage (Road):** Truck transport from the port of destination to the final destination facility.

## 3. Included Components

To ensure methodological robustness, the following components are explicitly included within the system boundary:

- **Distances:** Modeled road travel distances (using routing engines) and maritime sailing distances (using maritime networks).
- **Fuel Consumption:** Road diesel consumption (based on truck specifications and distances) and marine fuel consumption (based on vessel operational profiles and distances).
- **Port Operations:** Port handling, hoteling, and vessel auxiliary energy represented by the selected backend model. Port-specific observations are used when available; missing values are not interpreted as zero and are resolved through the documented fallback hierarchy where defensible. Separate hoteling is not added when the selected transport-work intensity already covers operational fuel, to avoid double counting.
- **Costs:** Fuel and operational cost estimates based on available diesel, marine fuel, and port-operation inputs. These are model estimates/proxies, not full commercial freight rates unless explicitly expanded in a future model boundary.
- **Emissions:** Operational tank-to-wheel/tank-to-wake (TTW) CO2e resulting from fuel combustion under the current model boundary. CO2-only, WTW, and LCA values from literature should not be substituted or compared directly unless the boundary is explicitly changed and documented.
- **Data Persistence:** Persisted scenario results, serving as an auditable output layer for all evaluated routes and comparisons.

## 4. Excluded Components

To maintain a clear and feasible scope focused on operational differences, the following components are excluded from the system boundary:

- **Manufacturing:** Vehicle (truck) and vessel manufacturing, maintenance, and end-of-life disposal.
- **Infrastructure:** Construction, maintenance, and end-of-life of infrastructure (roads, ports, terminals).
- **Full Life-Cycle:** Well-to-tank (upstream) emissions for fuels, unless explicitly noted; the focus is on tank-to-wheel/tank-to-wake (operational) emissions.
- **Unmodeled Terminal Loads:** Terminal loads outside the current moves-based port-operations boundary, such as reefers, non-handling building energy, or equipment categories without a defensible factor.
- **Externalities:** Accidents, congestion, noise, insurance, theft, and broader social externalities.
- **Market Dynamics:** Contract-specific freight rates, tariffs, inventory cost, and fluctuating spot market prices (the focus is on operational cost estimates rather than commercial pricing).

## 5. Boundary Risks

The chosen system boundaries introduce certain limitations that must be addressed transparently in the final thesis to prevent misinterpretation:

- **CO2 vs CO2e Confusion:** Results labeled only as "emissions" can be misread as CO2-only or lifecycle CO2e. Outputs should state the gas metric and boundary, especially when compared with literature values.
- **Port Emissions Coverage:** Port-operation and hoteling values have lower confidence when they rely on weighted peer averages or documented defaults rather than observed port-specific data. Components marked `unavailable` are explicitly not included without defensible data, and the result should be interpreted as incomplete for that component. Components marked `zero_activity` are zero because the represented activity is zero, not because data are missing.
- **Operational vs. Life-Cycle Scope:** Focusing primarily on operational (tank-to-wheel/wake) emissions does not capture the full life-cycle impacts, potentially missing differences in upstream fuel production emissions between diesel and marine fuels.
- **Modeled vs. Real-World Routes:** Relying on modeled distances (road routing and generalized sea networks) may differ from actual contracted routes or temporary operational detours.
- **Maritime Distance Provenance:** Sea-leg distance source affects route confidence and should be shown beside results when available. Route-quality warnings, including the current `50 km` minimum meaningful sea-leg threshold, are interpretation heuristics only; they are not model formulas, hard validation rules, or route optimization constraints.
- **Averages and Aggregation:** Using average consumption assumptions, typical vessel profiles, or standard truck types may hide significant operational variability caused by weather, vessel age, driver behavior, or specific cargo characteristics.
- **Cost Boundary:** Model cost estimates should not be interpreted as complete freight quotes because many commercial cost components are outside the current system boundary.

## 6. Recommended Thesis Wording

The following wording is suggested for inclusion in the methodology chapter of the final thesis:

> *"The functional unit for this study is defined as the transportation of a specific mass of containerized cargo between an origin and destination within Brazil. To ensure comparability, results are expressed in absolute terms per shipment, as well as normalized per tonne and per tonne-kilometer (t-km). The system boundary focuses on operational tank-to-wheel and tank-to-wake CO2e. For the road-only scenario, this encompasses direct truck haulage. For the multimodal scenario, the boundary includes origin road drayage, port operations and hoteling at port calls when separately supported by the selected model boundary, maritime sailing, and destination road drayage. When port-specific hotelling or port-operation data are available, these values are used directly. When such data are missing, the model avoids interpreting missing data as zero emissions. Instead, it applies a transparent fallback hierarchy: first a weighted average intensity from observed peer ports, then an existing documented default if no observed peer basis is available, and finally an explicit unavailable state when no defensible value can be assigned. Separate hoteling is excluded when the selected transport-work intensity already covers operational fuel. Source levels and fallback warnings are retained in the runtime output to support interpretation of result confidence. Consequently, this study excludes upstream life-cycle emissions, infrastructure construction, vehicle manufacturing, and unmodeled terminal loads outside the selected port-operations boundary. Cost outputs are interpreted as model cost estimates under the selected operational boundary, not as complete commercial freight rates."*
