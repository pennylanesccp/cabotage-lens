# Claim to Source Matrix

This matrix maps claims made in the CabotageLens thesis/report to supporting sources from the literature audit.

| Claim | Recommended Source(s) | Strength of Support | Boundary Caveat | Already in Docs? | Recommended Insertion Point | Recommended Wording / Caution |
|---|---|---|---|---|---|---|
| Brazilian freight is road-heavy. | `icct2022` | Strong (Page 2) | N/A | Yes | Intro / Context | Ensure citation is present when making the claim. |
| Cabotage is relevant in Brazil but underused. | `icct2022`, `competitiveness2024` | Strong (ICCT Page 2) | N/A | Yes | Intro / Context | Frame as an opportunity for decarbonization. |
| Cabotage can be environmentally favorable, but not universally. | `shortsea2019`, `isoemission2019` | Moderate (ShortSea2019 Abstract) | CO2 vs CO2e | Yes | Discussion / Results | Highlight that route-specific analysis is required to prove favorability. |
| Door-to-door comparison is necessary. | `competitiveness2024`, `modalshiftreview2020` | Strong (competitiveness) / Moderate (modalshift) | Cost/Emissions | Yes | Methodology | "As emphasized by [citation], comparisons limited to the main leg are insufficient." |
| Comparing only truck versus ship is insufficient. | `shortsea2019`, `modalshiftreview2020` | Moderate (Abstracts only) | N/A | Yes | Methodology | Ensure first/last mile are always explicitly modeled. |
| Short sea/cabotage results depend on corridor, port access, route distance, vessel utilization, and service feasibility. | `competitiveness2024`, `sssfactors2018` | Strong (competitiveness) / Moderate (ShortSea2019 Abstract) | N/A | Yes | Limitations / Discussion | Emphasize utilization and feasibility alongside distance. |
| Maritime cabotage competitiveness is stronger on some long-haul corridors. | `competitiveness2024` | Strong (Page 1 - 1800km threshold) | N/A | Yes | Results | Validate with CabotageLens outputs. |
| Pre-carriage and on-carriage can affect both cost and emissions. | `shortsea2019`, `competitiveness2024` | Strong | N/A | Yes | Methodology | Crucial for explaining cases where road wins. |
| TTW, WTW, and LCA boundaries must not be mixed. | `maritimelca2024` | Weak (Evidence missing) | System boundary | Yes | Methodology / Limitations | "This study focuses on [Boundary] to avoid conflation of lifecycle scopes." |
| CO2 and CO2e must not be mixed without explanation. | `decarb2024`, `icct2022` | Strong (Decarb2024 Page 1) | Gas species | Yes | Methodology | Explicitly define whether output is CO2 or CO2e. |
| Nearest-port logic is a simplification, not a full service-network model. | `competitiveness2024` | Strong (Page 1) | Service feasibility | Yes | Limitations | "Nearest-port routing approximates commercial reality and may select unserved pairs." |
| Haversine maritime distance is not sufficient for strong corridor conclusions. | `competitiveness2024` | Strong | Distance metrics | Yes | Methodology / Validation | Note the Batch 001 validation findings regarding SeaMatrix fallback. |
| Port operations and hoteling can matter but must be handled carefully to avoid double counting. | `berth2009`, `shipops2022` | Weak (Evidence missing) | TTW / Time-in-port | Yes | Port Ops Model | Clearly bound hoteling time and exclude main engine if off. |
| Cost outputs should not be presented as full commercial freight rates unless the boundary matches. | `competitiveness2024` | Moderate (Expected in full text) | Cost boundaries | Yes | Limitations | "Costs represent operational estimates, not fully burdened commercial freight rates." |
| Validation and sensitivity analysis are necessary before making strong conclusions. | `modalshiftreview2020` | Moderate (Abstract level review) | N/A | Yes | Methodology / Conclusion | Tie back to the TF validation plan. |
