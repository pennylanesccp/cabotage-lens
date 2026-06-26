# Recommended Methodology Updates

This document lists proposed changes or additions to the TF/report/article based on the literature audit. These are recommendations only and have not been applied to the codebase or main documentation.

## Second-pass summary

* **What became stronger**: The theoretical frameworks and boundary definitions (e.g., TTW vs WTW, CO2 vs CO2e) have been clearly mapped to specific papers in the matrix, establishing a strong structural foundation for the thesis methodology.
* **What remains uncertain**: Because the PDFs could not be parsed in the current environment, all specific quantitative values (emissions factors, utilization rates, average distances) remain unverified. The strength of support for all claims has been downgraded to `Weak (Evidence missing)` until the numbers and page references can be extracted manually.
* **What should be reviewed next**: A manual review of the five core papers is required to extract the exact tables and figures for fuel emissions factors, truck emissions baselines, and cabotage utilization rates.

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
  * **Source**: `shipops2022`
  * **Affected Document**: `hoteling_model.md`
  * **Reason**: Validates that the 2009 base data is still reasonably accurate or bounds the error.
  * **Risk if ignored**: Minor criticism on data recency.
  * **Proposed Action**: Compare current model factors with the 2022 paper's findings.
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

## Do Not Include / Outside Current Boundary

* **Recommendation**: Advanced Machine Learning for Shapley Value cost allocation.
  * **Source**: `shapley2025`
  * **Affected Document**: N/A
  * **Reason**: Too far outside the current scope of the tool's cost models.
  * **Risk if ignored**: None.
  * **Proposed Action**: Ignore.
  * **Requires Code Change**: No.
  * **Priority**: Low
