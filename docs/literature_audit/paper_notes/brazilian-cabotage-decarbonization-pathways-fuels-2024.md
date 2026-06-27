# Paper Note: Decarbonization pathways in Brazilian maritime cabotage

* **Full Title**: Decarbonization pathways in Brazilian maritime cabotage: A comparative analysis of very low sulfur fuel oil, marine diesel oil, and hydrogenated vegetable oil in carbon dioxide equivalent emissions
* **Year**: 2024
* **Local File Path / Citation Key**: `docs/references/core/brazilian-cabotage-decarbonization-pathways-fuels-2024.pdf` / `decarb2024`
* **Review Status**: reviewed
* **Extraction Method**: Text extraction using `pypdf` via a local Python script, followed by targeted text and keyword context queries.
* **What part of the paper was actually read**: Abstract (Page 1), Introduction (Pages 1-3), fuel consumption parameters from Brazilian operators (Page 4, Section 4.2), mathematical models for emission calculation (Page 4, Section 4.3), emission factors (Page 5, Table 1), and HVO reduction results (Page 6).
* **Key claims relevant to CabotageLens**:
  - Transitioning from VLSFO/MDO to HVO (Hydrogenated Vegetable Oil) can reduce annual emissions in Brazilian cabotage by 75.4%.
  - Establishes a clear lifecycle (WTW) framework for maritime emissions in Brazil, specifying lower heating values (LHV) and carbon intensities.
* **Exact section/page/table/figure references**:
  - Page 1 (Abstract): 75.4% emission reduction potential and absolute tonnage values (reduction from 1,395,466 to 343,950 tons CO2e/year).
  - Page 4 (Section 4.2): Average ship consumption parameters (3.5 tons/day steaming, 5.0 tons/day port).
  - Page 5 (Table 1): WTW and energy content parameters for HVO, VLSFO, and MDO (source EPE 2023 for HVO, IMO MEPC.391(81) for VLSFO/MDO).
  - Page 7 (Section 4.3): Standard navigation duration of 2 hours at 10 knots assumed for pilot station entry/exit.
* **Useful quantitative values, with units**:
  - **Vessel Fuel Consumption in Voyage**: 3.5 tons/day of MDO/VLSFO during sea voyages (Page 4, Section 4.2; sourced from a prominent Brazilian shipping company's container liner schedule).
  - **Vessel Fuel Consumption in Port (Hoteling)**: 5.0 tons/day of MDO while docked at ports (Page 4, Section 4.2; sourced from a prominent Brazilian shipping company's container liner schedule).
  - **HVO WTW Emission Factor**: 23.7 gCO2e/MJ (Page 5, Table 1; source EPE 2023). Well-to-Wake (WTW) lifecycle boundary.
  - **HVO Lower Heating Value (LHV)**: 37.68 MJ/kg (Page 5, Table 1).
  - **MDO WTW Emission Factor**: 93.8 gCO2e/MJ (Page 5, Table 1; source IMO 2020 Fourth GHG Study). Well-to-Wake (WTW) lifecycle boundary.
  - **MDO Lower Heating Value (LHV)**: 42.7 MJ/kg (Page 5, Table 1).
  - **VLSFO WTW Emission Factor**: 93.8 gCO2e/MJ (Page 5, Table 1; source IMO 2020 Fourth GHG Study). Well-to-Wake (WTW) lifecycle boundary.
  - **VLSFO Lower Heating Value (LHV)**: 40.2 MJ/kg (Page 5, Table 1).
  - **Port Entry/Exit Navigation Buffer**: Assumed standard navigation duration of 2 hours at a speed of 10 knots per port call to calculate VLSFO consumption during vessel entry/exit (Page 7).
* **Emissions boundary**: Well-to-Wake (WTW) / CO2e. Employs the WTW framework dividing emissions into Well-to-Tank (production) and Tank-to-Wake (combustion) using 100-year GWP values.
* **Cost boundary**: N/A (Focuses strictly on operational fuel consumption and emissions).
* **Route/network modeling boundary**: Uses operational schedules from four leading Brazilian container cabotage companies between Brazilian ports (from Pilot Station to Pilot Station).
* **Direct implications for CabotageLens methodology**:
  - Sourced vessel consumption parameters (3.5 t/day steaming vs 5.0 t/day hoteling) are highly valuable for refining or validating CabotageLens' fuel models.
  - Explains the importance of hoteling and port entry/exit modeling (2-hour navigation buffer).
* **Caveats and non-applicable parts**: The paper's emissions factors are WTW lifecycle values, which are broader than the pure Tank-to-Wake (TTW) combustion factors modeled in CabotageLens.
* **Claims that should not be borrowed because the boundary differs**:
  - Do not use the WTW emission factors (23.7 gCO2e/MJ for HVO, 93.8 gCO2e/MJ for MDO/VLSFO) directly as combustion emission factors in CabotageLens, as they include fuel production emissions.
* **Recommended citation use**: Cite for the 3.5 t/day voyage and 5.0 t/day port consumption rates of Brazilian cabotage container ships, and for HVO decarbonization potential.
