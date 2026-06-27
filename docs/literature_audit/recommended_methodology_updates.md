# Recommended Methodology Updates

This document lists proposed changes or additions to the TF/report/article based on the literature audit. These are recommendations only and have not been applied to the codebase or main documentation.

## Latest-pass summary

* **What was actually extracted**:
  * `competitiveness2024`: Competitiveness distance threshold of >1,800 km (Page 18); VLSFO WTW emission factor of 94.26 gCO2eq/MJ and MDO WTW emission factor of 92.78 gCO2eq/MJ (Page 20, Table 13); and road transportation EBIT margin of 15% (Page 5).
  * `icct2022`: Cabotage emission intensity of 8 gCO2/TKU vs road transport emission intensity of 52 gCO2/TKU (Page 12); road freight rate premium of 20% on average (Page 2); and 2020 cabotage sector emissions of 4.7 million tonnes of CO2e (Page 14).
  * `decarb2024`: Vessel fuel consumption of 3.5 tons/day during voyage vs 5.0 tons/day in port (Page 4); HVO WTW emission factor of 23.7 gCO2e/MJ (Page 5, Table 1); and a 75.4% emission reduction potential by switching from VLSFO/MDO to HVO.
  * `shortsea2019` (partial): Feeder vessel CO2 emissions of 582, 654, and 718 gCO2/TEU-km (Page 7, Table 3) depending on ship size (458–809 TEU).
* **What became stronger**: Support for Brazilian-specific freight matrix claims (high road-dependency), macro emissions disparities (8g vs 52g CO2/TKU), average operational fuel consumption for cabotage vessels (3.5 t/day steaming, 5.0 t/day port), and the distance threshold at which cabotage becomes cost-competitive (>1,800 km).
* **What remains partial**: Analysis of European container feeder operations (`shortsea2019`) and the global modal shift review (`modalshiftreview2020`) remain partial (limited to abstract/intro and key results). Consequently, their support in the claim matrix is downgraded to **Moderate**. The micro-level parameters for port terminal operations (such as actual port crane handling rates or port dwell times in Brazil) remain unextracted from the literature.
* **What should be reviewed next**: Non-core papers focusing on at-berth/hoteling emissions (e.g. `berth2009`, `shipops2022`) and primary sources of Brazilian port performance (such as ANTAQ or port authority datasets) should be audited next to refine the hoteling and port operation model inputs.


## Must Include Before Final Report

* **Recommendation**: Explicitly specify CO2 vs CO2e in all outputs and text.
  * **Source**: `decarb2024`, `icct2022`
  * **Affected Document**: `tf_system_boundary.md`, all UI labels.
  * **Reason**: Academic rigor; mixing gas species invalidates comparative results.
  * **Risk if ignored**: Critical methodology flaw during examination.
  * **Proposed Action**: Audit terminology and standardize on the selected metric.
  * **Requires Code Change**: Yes (UI labels).
  * **Priority**: High

* **Recommendation**: State clearly that cost outputs are operational estimates, not commercial freight rates.
  * **Source**: `competitiveness2024`
  * **Affected Document**: `tf_assumptions_and_approximations.md`
  * **Reason**: Prevents misinterpretation of the economic feasibility.
  * **Risk if ignored**: Examiner might question the commercial realism of the costs.
  * **Proposed Action**: Add a dedicated "Cost Boundary" section to assumptions.
  * **Requires Code Change**: No.
  * **Priority**: High

* **Recommendation**: Address the haversine maritime distance fallback issue.
  * **Source**: Validation Batch 001, `competitiveness2024`
  * **Affected Document**: `tf_validation_batch_001_correction_plan.md` (Execution)
  * **Reason**: Haversine underestimates true maritime distance, biasing results in favor of cabotage.
  * **Risk if ignored**: Invalid distance and emissions outputs for affected corridors.
  * **Proposed Action**: Implement bounding or correction for the fallback.
  * **Requires Code Change**: Yes.
  * **Priority**: High

## Should Include If Time Allows

* **Recommendation**: Contrast nearest-port logic with multimodal supernetwork models.
  * **Source**: `competitiveness2024`
  * **Affected Document**: `tf_limitations.md` (or similar section in the final report).
  * **Reason**: Demonstrates awareness of state-of-the-art modeling techniques.
  * **Risk if ignored**: Missed opportunity for a strong academic discussion section.
  * **Proposed Action**: Add a paragraph discussing supernetworks as the next level of fidelity.
  * **Requires Code Change**: No.
  * **Priority**: Medium

* **Recommendation**: Update hoteling emissions factors with modern data if current baseline is too old.
  * **Source**: `shipops2022`, `decarb2024`
  * **Affected Document**: `hoteling_model.md`
  * **Reason**: Validates that the 2009 base data is still reasonably accurate or bounds the error.
  * **Risk if ignored**: Minor criticism on data recency.
  * **Proposed Action**: Compare current model factors with the 2024 paper's findings (5.0 tons/day in port).
  * **Requires Code Change**: Maybe (if factors need adjusting).
  * **Priority**: Medium

## Useful for Discussion/Limitations

* **Recommendation**: Discuss market and policy barriers to modal shift.
  * **Source**: `modalshiftreview2020`, `sssfactors2018`
  * **Affected Document**: Final TF Report (Discussion)
  * **Reason**: Acknowledges that emissions/cost advantages don't automatically guarantee adoption.
  * **Risk if ignored**: The conclusion might appear overly optimistic.
  * **Proposed Action**: Draft a "Barriers to Implementation" subsection.
  * **Requires Code Change**: No.
  * **Priority**: Low

## Future Work Only

* **Recommendation**: Implement WTW / LCA emissions boundaries.
  * **Source**: `maritimelca2024`, `decarb2024`
  * **Affected Document**: Final TF Report (Future Work)
  * **Reason**: Provides a more comprehensive environmental footprint, especially for alternative fuels.
  * **Risk if ignored**: None, as long as TTW is clearly stated.
  * **Proposed Action**: List LCA integration as future work.
  * **Requires Code Change**: No.
  * **Priority**: Low

* **Recommendation**: Integrate actual service networks (schedules, frequencies).
  * **Source**: `competitiveness2024`
  * **Affected Document**: Final TF Report (Future Work)
  * **Reason**: Moves from theoretical viability to commercial feasibility.
  * **Risk if ignored**: None.
  * **Proposed Action**: List supernetwork integration as future work.
  * **Requires Code Change**: No.
  * **Priority**: Low

