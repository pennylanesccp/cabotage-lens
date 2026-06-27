# Paper Note: Brazilian coastal shipping: New prospects for growth with decarbonization

* **Full Title**: Brazilian coastal shipping: New prospects for growth with decarbonization
* **Year**: 2022
* **Local File Path / Citation Key**: `docs/references/core/brazilian-coastal-shipping-decarbonization-2022.pdf` / `icct2022`
* **Review Status**: reviewed
* **Extraction Method**: Text extraction using `pypdf` via a local Python script, followed by targeted text and keyword context queries.
* **What part of the paper was actually read**: Executive Summary (Page 2), Brazilian transport matrix context (Page 2), fleet composition (Page 4), operating costs (Page 9, Fig 8), fuel tax policies (Page 10), and emission intensity comparisons (Page 12, Page 14, Fig 10).
* **Key claims relevant to CabotageLens**:
  - Brazilian freight is heavily dependent on road transport (64% modal share). Cabotage is underutilized (11% of cargo transported, measured in TKU).
  - Cabotage is significantly more CO2-efficient than road transport on a ton-kilometer basis.
  - Road transport freight rates are on average 20% higher than cabotage rates.
* **Exact section/page/table/figure references**:
  - Page 2 (Executive Summary): Modal shares (11% cabotage, 64% road), and road rates being on average 20% higher.
  - Page 4 (Figure 1): Ship types in Brazilian cabotage (63% oil tankers, 20% container ships, 10% dry bulk).
  - Page 9 (Figure 8): Operating cost structure of cabotage (Fuel 44%, Taxes 20%, Other 13%, Maintenance 8%, Administrative 7%, Crew 5%, Insurance 3%).
  - Page 10 (Section 7): Local ICMS tax and fuel price discrepancies (vessels pay 20% more for fuel than vessels in international transport).
  - Page 12 (Section 9): Micro-level emission comparison (8 gCO2/TKU for cabotage vs 52 gCO2/TKU for road transport).
  - Page 14 (Figure 10): 2020 cabotage emissions total of 4.7 million tonnes of CO2e.
* **Useful quantitative values, with units**:
  - **Cabotage Emission Intensity**: 8 gCO2/TKU (Page 12, Footnote 9 / Text; source EPL 2021). Tank-to-Wake (TTW) CO2 combustion boundary.
  - **Road Transport Emission Intensity**: 52 gCO2/TKU (Page 12, Footnote 9 / Text; source EPL 2021). Tank-to-Wake (TTW) CO2 combustion boundary.
  - **Road Freight Rate Premium**: On average 20% higher than cabotage rates (Page 2, Executive Summary; source Alvarenga 2019). Commercial freight rate boundary.
  - **Cabotage Fleet Fuel Cost Share**: 44% of total operational cost (Page 9, Figure 8).
  - **Fuel Cost Surcharge**: Cabotage vessels pay ~20% more for fuel than international vessels due to ICMS tax (Page 10, Section 7).
  - **Cabotage Sector Emissions (2020)**: 4.7 million tonnes of CO2e (Page 14, Figure 10; based on Comer & Osipova 2021 and MEPC 2018 factors, using IPCC AR6 100-year GWP: CH4 = 29.8, N2O = 273).
* **Emissions boundary**: Tank-to-Wake (TTW) / CO2 and CO2e. The micro comparison (8g vs 52g) is stated as CO2 (combustion only). The macro sector estimates (4.7M tonnes) are reported as CO2e using IPCC AR6 100-year GWP values.
* **Cost boundary**: Commercial freight rates for the 20% premium claim; operational cost breakdown for the 44% fuel cost claim.
* **Route/network modeling boundary**: National macro-level averages.
* **Direct implications for CabotageLens methodology**:
  - Confirms Tank-to-Wake (TTW) as the primary operational boundary for comparing combustion emissions.
  - Provides a Brazilian-specific benchmark (8g vs 52g CO2/TKU) to validate or compare CabotageLens' output results.
* **Caveats and non-applicable parts**: The 20% road freight premium is a national average and does not account for specific multimodal routes where road-only might be cheaper due to short distance or high port handling costs.
* **Claims that should not be borrowed because the boundary differs**:
  - Do not use the 8 gCO2/TKU and 52 gCO2/TKU as direct substitutes for corridor-specific calculations, as they represent cargo-aggregated national estimates.
  - Do not assume fuel price local surcharges (20% more) apply uniformly across all states, due to variable ICMS tax exemptions.
* **Recommended citation use**: Cite for the modal share statistics of Brazil, the 8g vs 52g CO2/TKU emission intensity comparison, and the 20% average road rate premium.
