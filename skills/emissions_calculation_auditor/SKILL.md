---
name: emissions_calculation_auditor
description: Numerical logic, unit conversions, emissions species, system-boundary, baseline/sensitivity/benchmark/diagnostic classification, and formula audits for CabotageLens maritime cabotage and road emissions calculations.
---

# Emissions Calculation Auditor Skill

## 1. Purpose
This skill provides a rigorous calculation-auditor workflow for reviewing, validating, and debugging mathematical formulas, unit conversions, conversion factors, emission factors, system boundaries, and numeric result interpretation in the CabotageLens project. It prevents hidden methodology bugs in calculations comparing road transport versus maritime cabotage.

## 2. When to Use
Trigger this skill when:
- Reviewing, modifying, or writing code inside calculation modules (e.g., in `modules/` or `calcs/`).
- Validating emissions results, fuel consumption coefficients, energy density values, or GWP (Global Warming Potential) indices.
- Verifying the mathematical consistency of equations in reports, documentation, or user-facing Streamlit summaries.
- Modifying emission modeling inputs (e.g., road vs. cabotage transport legs, port terminal operations, or hotelling models).

## 3. Inputs Expected
The agent expects or must locate:
- Code files containing calculation models and formulas (e.g., in `modules/` or `calcs/`).
- Methodology documentation files (e.g., `docs/methodology_audit.md`, `docs/hoteling_model.md`, `docs/port_ops_model.md`).
- Input parameter databases or builders (e.g., data parameters under `data/` or parameter builders in `calcs/`).
- The specific formula, equation, or code snippet under audit.

## 4. Step-by-Step Audit Workflow
1. **Locate and Extract**: Identify the code or document sections containing the calculations, constants, and unit conversions.
2. **Determine Boundaries**: Identify the greenhouse gases covered ($\text{CO}_2$ vs. $\text{CO}_{2\text{eq}}$) and lifecycle boundaries: Well-to-Tank (WTT), Tank-to-Wake (TTW for maritime) / Tank-to-Wheel (TTW for road), or Well-to-Wake (WTW for maritime) / Well-to-Wheel (WTW for road).
3. **Trace Conversion Factors**: Audit every conversion factor (e.g., density, specific gravity, energy density, emissions factor per fuel unit).
4. **Perform Dimensional Analysis**: Trace units through every step of the equation to ensure the final output matches the expected physical dimension.
5. **Verify Equitable Comparison**: Verify if the road and cabotage modes are evaluated over equivalent boundaries (including pre/on-carriage, terminal handling, and correct distance routing).
6. **Classify Data Inputs**: Classify calculation inputs as *Observed/Measured Data*, *Literature Values*, *Project Assumptions*, or *Fallbacks/Approximations*.
7. **Run Checklists**: Run through the audit checklists in Sections 5-10.
8. **Draft Findings & Recommendations**: Compile the audit findings, pointing out specific red flags, corrected equations, and recommended validation steps.

## 5. Unit and Dimensional Consistency Checklist
Verify the following unit mappings and conversions:
- [ ] **Mass**: Are conversions between grams ($\text{g}$), kilograms ($\text{kg}$), tonnes ($\text{t}$), and short/metric tons correct and explicit?
- [ ] **Distance**: Are distances properly defined? (e.g., road distance in km, sea distance in nautical miles ($\text{NM}$), and conversion factor $1\text{ NM} = 1.852\text{ km}$ applied correctly).
- [ ] **Transport Work**: Are work units correctly calculated as tonne-kilometer ($\text{t}\cdot\text{km}$) or TEU-kilometer ($\text{TEU}\cdot\text{km}$)?
- [ ] **Fuel Volume to Mass**: Is fuel density used correctly when converting volume (liters, $\text{m}^3$) to mass (tonnes, $\text{kg}$)?
- [ ] **Energy Conversion**: Are conversions between fuel volume/mass, energy content (megajoules $\text{MJ}$, kilowatt-hours $\text{kWh}$), and lower/higher heating values ($\text{LHV}/\text{HHV}$) explicit and mathematically sound?
- [ ] **Emission Intensity**: Do the units of emission factors (e.g., $\text{g/kWh}$, $\text{g/MJ}$, $\text{kg/t of fuel}$) match the units of the activity data they multiply?
- [ ] **Output Scaling**: Are final outputs clearly scaled? (e.g., annual emissions in $\text{t CO}_2\text{/year}$, per-trip emissions in $\text{kg CO}_{2\text{eq}}$, per-TEU, per-tonne, or intensity in $\text{g CO}_{2\text{eq}}\text{/t}\cdot\text{km}$).

## 6. Emissions Boundary Checklist
Verify the scope of the calculation boundary:
- [ ] **Lifecycle Boundaries**: Is the distinction between TTW (direct combustion: Tank-to-Wake for maritime, Tank-to-Wheel for road), WTT (Well-to-Tank fuel extraction/refining/transport), and WTW (sum of TTW and WTT: Well-to-Wake for maritime, Well-to-Wheel for road) maintained correctly in formulas and labels?
- [ ] **Carbon Species**: Are $\text{CO}_2$-only factors clearly separated from $\text{CO}_{2\text{eq}}$ factors (which include $\text{CH}_4$, $\text{N}_2\text{O}$, etc., based on GWP horizons)?
- [ ] **Equivalent Scope**: When comparing road and cabotage, are all relevant legs accounted for?
  - Road leg: Direct origin-to-destination road transit.
  - Cabotage leg: Pre-carriage road leg + port terminal operations (handling/gate) + maritime voyage leg (including maneuvering and hotelling at berths) + on-carriage road leg.

## 7. CabotageLens Current Emissions Guardrails
- Current baseline report outputs are operational TTW $\text{CO}_{2\text{eq}}$ unless explicitly stated otherwise.
- Do not combine operational TTW $\text{CO}_{2\text{eq}}$ outputs with WTW, LCA, $\text{CO}_2$-only, or other $\text{CO}_{2\text{eq}}$ boundaries without explicit reconciliation.
- Road-factor reconciliation using `0.8602944 kgCO2e/km` is diagnostic benchmark alignment only.
- Do not replace baseline road emissions with the diagnostic factor unless a task explicitly asks for a separate diagnostic scenario.
- Batch 002 directional agreement does not validate exact emissions magnitude.
- Route-cache stability does not validate commercial route availability or operational service availability.
- Values from uploaded literature must not be inserted as coefficients unless the current methodology explicitly adopts them and tracks provenance.
- If a number is not in tracked project artifacts, do not invent it and do not silently derive it.

## 8. Formula Review Checklist
Validate the mathematical logic of the equations:
- [ ] **Energy-Efficiency Formula**: Ensure engine power, load factors (MCR%), speed, and specific fuel oil consumption (SFOC) are integrated correctly:
  $$\text{Fuel Consumption} = \text{Power (kW)} \times \text{Load Factor} \times \text{SFOC (g/kWh)} \times \text{Time (h)}$$
- [ ] **Transport Allocations**: Ensure cargo weight is correctly allocated to emissions (e.g., TEU-based, weight-based, or volume-based allocations).
- [ ] **Aggregation Bias**: Ensure that averages are weighted correctly (e.g., average emissions intensity must be weighted by cargo-work $\text{t}\cdot\text{km}$, not a simple average of trip intensities).

## 9. Data Quality and Fallback Checklist
Ensure parameters are handled rigorously:
- [ ] **No Inventions**: Do not invent coefficients, emissions factors, fuel prices, vessel parameters, load factors, or engine parameters.
- [ ] **No Arbitrary Guessing**: Do not "pick reasonable values" for missing variables. If a parameter is missing, explicitly flag it, search authoritative references, or treat it as a transparent, documented assumption/fallback.
- [ ] **Observed vs. Fallback**: Check if default fallbacks are only applied when primary observed data is unavailable, and that the switch to fallback is logged or surfaced.

## 10. Output Interpretation Checklist
Validate user-facing results and academic defensibility:
- [ ] **Justified Precision**: Ensure display values are rounded appropriately to reflect input data uncertainty (e.g., do not display emissions down to the gram if distances or payloads are rough estimates).
- [ ] **Data Loss & Filter Disclosures**: Ensure that any calculations omitting data (e.g., skipped routes, failed geocoding fallbacks, or unrepresentative outliers) explicitly disclose the data loss or filtering criteria.
- [ ] **Emissions Species**: Does every substantive audit report whether the value is $\text{CO}_2$ or $\text{CO}_{2\text{eq}}$?
- [ ] **Boundary Label**: Does it report whether the value is TTW, WTT, WTW, LCA, or another boundary?
- [ ] **Result Role**: Does it classify the value as baseline, sensitivity, benchmark, diagnostic, or future-work context?
- [ ] **Thesis Impact**: Does it state whether the finding affects Chapter 6/7/8/9 thesis claims?

## 11. Red Flags / Things to Reject
Reject the following methodological bugs:
- **Interchangeable CO2/CO2eq**: Treating $\text{CO}_2$ emissions factors as representative of total $\text{CO}_{2\text{eq}}$ without greenhouse gas scaling.
- **Unit Mismatch**: Adding or multiplying incompatible units (e.g., adding TTW $\text{CO}_2$ directly to WTW $\text{CO}_{2\text{eq}}$).
- **Asymmetric Comparisons**: Comparing road transport WTW emissions with cabotage TTW emissions, or ignoring port terminal handling emissions in the multimodal chain.
- **Incorrect Distance Bases**: Multiplying maritime emissions factors (which are based on nautical miles or sea routes) by straight-line (great-circle) distances without detour factors, or mixing them with road kilometer bases without conversion.

## 12. Expected Outputs
Depending on the size of the task, the agent must produce:

- **For Small Checks / Minor Edits**:
  - A concise, bulleted list of findings, unit checks, and required corrections.

- **For Substantive Audits / Calculation Reviews**:
  1. **Audited Formula/Calculation Summary**: A mathematical summary of the audited equations and variables.
  2. **Unit Consistency Assessment**: A dimensional verification proof showing that the units balance correctly.
  3. **Assumptions & Data-Source Classification**: A table separating Observed, Literature, Project Assumptions, and Fallback parameters.
  4. **Boundary Definition**: Explicit statement of TTW/WTT/WTW (defining Tank-to-Wake/Well-to-Wake for maritime, and Tank-to-Wheel/Well-to-Wheel for road) and $\text{CO}_2$/$\text{CO}_{2\text{eq}}$ boundaries.
  5. **Result Role Classification**: State whether each value is baseline, sensitivity, benchmark, diagnostic, or future-work context, and whether it affects Chapter 6/7/8/9 claims.
  6. **Red Flags or Required Corrections**: Clear list of any detected calculation bugs or risks.
  7. **Recommended Validation Steps**: Actionable testing or coding validation steps to verify the numerical outputs.

## 13. Language Rule
- Match the user request and target artifact language.
- For academic report text in this project, default to Portuguese unless the target file or user request is in English.
- Technical variable names, formulas, code identifiers, and terminal/log metrics may remain in English.

## 14. Non-Goals
- Performing academic literature audits or writing introductory text (this is covered by the `academic_maritime_research` skill).
- Modifying application UI components, database schemas, or styling files unless the user explicitly requests calculation logic implementation in those areas.
