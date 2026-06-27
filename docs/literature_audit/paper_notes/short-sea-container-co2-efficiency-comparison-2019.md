# Paper Note: The comparative CO2 efficiency of short sea container transport

* **Full Title**: The comparative CO2 efficiency of short sea container transport
* **Year**: 2019
* **Local File Path / Citation Key**: `docs/references/core/short-sea-container-co2-efficiency-comparison-2019.pdf` / `shortsea2019`
* **Review Status**: partial
* **Extraction Method**: Text extraction using `pypdf` via a local Python script, followed by targeted text and keyword context queries.
* **What part of the paper was actually read**: Abstract (Page 1), Introduction (Page 2), and key feeder vessel emissions results (Pages 7-8, Section 6) via automated text extraction.
* **Key claims relevant to CabotageLens**:
  - Short sea container shipping is generally more CO2-efficient than road haulage, but the comparative edge can be marginal in some scenarios.
  - Shipping services must obtain a fairly high capacity utilization to represent the green mode of transport in terms of CO2 emissions.
* **Exact section/page/table/figure references**:
  - Page 1 (Abstract): Highlights capacity utilization requirement.
  - Page 2 (Section 1): Global warming reduction policy targets (20% reduction within 2030 compared to 2008 levels), and literature ship emissions ranging from 10.8 to 25.8 gCO2/ton-km (Psaraftis & Kontovas 2009).
  - Page 7 (Section 6 / Table 3): Average vessel CO2 emissions per TEU-km (654 g/TEU-km, 582 g/TEU-km, and 718 g/TEU-km respectively for the three studied feeder vessels of capacity 458-809 TEUs).
  - Page 8 (Section 6): Mode-comparative analysis finding that the vessel has lower emissions per TEU-km than a road alternative under a 50% return-load scenario, but the edge shrinks as truck load factors increase.
* **Useful quantitative values, with units**:
  - **Vessel CO2 Emission Factors**: 654 gCO2/TEU-km, 582 gCO2/TEU-km, and 718 gCO2/TEU-km (Page 7, Table 3; based on actual operations over a full year for vessels ranging from 458 to 809 TEU). Tank-to-Wake (TTW) CO2 combustion boundary.
  - **Literature Ship Emission Range**: 10.8 to 25.8 gCO2/ton-km (Page 2, Section 1; source Psaraftis & Kontovas 2009). Tank-to-Wake (TTW) CO2 combustion boundary.
  - **Feeder Vessel Cargo Capacity**: 458 TEU, 809 TEU, and 650 TEU (Page 7 / Page 2).
* **Emissions boundary**: Tank-to-Wake (TTW) / CO2. Focused strictly on fuel combustion emissions of CO2, not CO2e or Well-to-Wake.
* **Cost boundary**: N/A (Focuses strictly on operational fuel efficiency and CO2).
* **Route/network modeling boundary**: Feeder container routes in Europe compared against counterfactual direct road transport routes serving the same origin-destination flows.
* **Direct implications for CabotageLens methodology**:
  - Confirms the importance of modeling container capacity utilization (load factors) in emissions comparisons.
  - Demonstrates that for short distances or routes with low maritime load factors, short sea shipping may lose its environmental advantage.
* **Caveats and non-applicable parts**: Analyzed container feeder routes are specific to Norway and Northern Europe, with vessel sizes (458-809 TEU) smaller than standard Brazilian cabotage vessels.
* **Claims that should not be borrowed because the boundary differs**:
  - Do not use the European feeder emissions factors (e.g., 582 gCO2/TEU-km) directly for Brazilian cabotage, as vessel sizes, speeds, and weather conditions differ.
* **Recommended citation use**: Use to support claims that short sea shipping's emissions advantage over road depends heavily on load factors/capacity utilization, and is not automatically superior on all corridors.
