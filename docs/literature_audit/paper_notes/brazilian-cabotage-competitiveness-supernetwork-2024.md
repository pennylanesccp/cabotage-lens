# Paper Note: Brazilian maritime containerized cabotage competitiveness assessment based on a multimodal super network

* **Full Title**: Brazilian maritime containerized cabotage competitiveness assessment based on a multimodal super network
* **Year**: 2024
* **Local File Path / Citation Key**: `docs/references/core/brazilian-cabotage-competitiveness-supernetwork-2024.pdf` / `competitiveness2024`
* **Review Status**: reviewed
* **Extraction Method**: Text extraction using `pypdf` via a local Python script, followed by targeted text and keyword context queries.
* **What part of the paper was actually read**: Abstract (Page 1), Introduction (Pages 1-2), cost function formulations (Pages 5-6), multimodal map and supernetwork details (Pages 9-10), distance threshold results (Page 18), and emissions parameters (Page 20, Table 13).
* **Key claims relevant to CabotageLens**:
  - Cabotage holds a significant cost advantage over road transportation for long-haul routes, particularly when distances exceed 1,800 km.
  - Maritime cabotage offers substantial environmental benefits, with CO2 equivalent emission reductions of up to 41.3%.
* **Exact section/page/table/figure references**:
  - Page 1 (Abstract): Competitiveness distance threshold and 41.3% emission reduction claim.
  - Page 5 (Section 4.1.2): Road EBIT margin specification.
  - Page 10 (Section 4.3): Multimodal map (Fig. 3), and EPE road emission parameters.
  - Page 11 (Table 1): Road parameters (EBIT margin, fuel consumption).
  - Page 18 (Section 5): Sensitivity analysis and distance competitiveness thresholds for different cabotage lines.
  - Page 20 (Table 13): Well-to-Wake (WTW) emissions parameters for VLSFO and MDO marine fuels.
* **Useful quantitative values, with units**:
  - **Distance Competitiveness Threshold**: >1,800 km (Page 18, Section 5; specifically over 1,800 km for Aliança, 2,200 km for Log-In, 2,419 km for Mercosul Line, and 2,508 km for Norcoast).
  - **Emissions Reduction Potential**: Up to 41.3% reduction in CO2e depending on route and company (Page 1, Abstract).
  - **VLSFO WTW Emission Factor**: 94.26 gCO2eq/MJ (Page 20, Table 13). WTW boundary (WtT = 16.8 gCO2eq/MJ, TtW = 77.46 gCO2eq/MJ).
  - **MDO WTW Emission Factor**: 92.78 gCO2eq/MJ (Page 20, Table 13). WTW boundary (WtT = 17.7 gCO2eq/MJ, TtW = 75.08 gCO2eq/MJ).
  - **Road Diesel WTW Emission Factor**: 86.50 gCO2eq/MJ (Page 10, Section 4.3; source EPE 2022). WTW boundary.
  - **Road Diesel Fuel Energy Content**: 35.52 MJ/liter (Page 10, Section 4.3).
  - **Road Diesel Fuel Consumption (6-axle truck)**: 0.28 liters/km (Page 11, Table 1; source CETESB 2021).
  - **Road Transportation EBIT Margin**: 15.0% (Page 5, Section 4.1.2; used to estimate commercial freight rates from road operational costs).
  - **Carbon Price**: 356.2 BRL/tCO2e (Page 11, Table 1; source Reuters 2024).
* **Emissions boundary**: Well-to-Wake (WTW) / CO2e. Integrates Well-to-Tank (WtT) upstream production and Tank-to-Wake (TtW) ship/truck combustion phases.
* **Cost boundary**: Multi-component logistics cost incorporating road/waterway freight rates (including a 15% road EBIT margin), in-transit inventory carrying costs, and carbon tax costs. Represents a modeled commercial logistics rate rather than pure vessel operational costs.
* **Route/network modeling boundary**: Supernetwork model of 637 cities, 18 container terminals, 8 barge terminals, and 301 maritime routes. Accounts for first-mile and last-mile road carriage.
* **Direct implications for CabotageLens methodology**:
  - Validates using a threshold (such as 1,800 km) for discussing cabotage competitiveness, but highlights that the threshold varies significantly by company/service frequency.
  - Demonstrates that WTW emissions factors (incorporating fuel production LCA) differ from pure combustion (TTW) factors.
* **Caveats and non-applicable parts**: The supernetwork model includes service frequency and inventory holding costs, which are not currently modeled in the CabotageLens UI.
* **Claims that should not be borrowed because the boundary differs**:
  - Do not directly substitute the 94.26 gCO2eq/MJ (VLSFO) or 92.78 gCO2eq/MJ (MDO) WTW emissions factors into CabotageLens' emissions calculations, as CabotageLens uses a Tank-to-Wake (TTW) combustion boundary.
  - Do not present CabotageLens' operational cost comparison as identical to this paper's cost impedance, which includes inventory capital cost and profit margins.
* **Recommended citation use**: Cite for the 1,800 km competitiveness threshold for Brazilian containerized cabotage and for the differentiation between WTW and TTW boundaries.
