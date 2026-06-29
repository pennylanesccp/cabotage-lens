---
name: academic_maritime_research
description: Technical guidelines and academic validation workflow for writing, reviewing, or validating research content, methodologies, and calculations regarding maritime cabotage, modal shift, and emissions.
---

# Academic Maritime/Naval Engineering Research Support Skill

## 1. Purpose
This skill provides a structured framework and rigorous step-by-step workflow for assisting with academic research, drafting, and validating methodologies for a Brazilian naval engineering final project / Trabalho de Formatura focused on maritime cabotage, modal shift, port operations, fuel consumption, $\text{CO}_2$/$\text{CO}_{2\text{eq}}$ emissions, and decarbonization.

## 2. When to Use
Trigger this skill when:
- Reviewing, modifying, or drafting academic documents (e.g., reports, articles, LaTeX draft `docs/tf.tex`, draft markdown files, or methodology documentation).
- Reviewing or updating calculations, formulas, coefficients, or equations related to vessel emissions, fuel consumption, road-versus-sea comparisons, and port operations in the `cabotage-lens` project.
- Evaluating literature reviews, citation maps, assumptions, or data reliability inventories related to maritime decarbonization or multimodal transport in Brazil.

## 3. Inputs Expected
The agent expects or must locate:
- Academic drafts and LaTeX source files (e.g., `docs/tf_final_report_draft.md`, `docs/tf.tex`).
- Methodological descriptions (e.g., `docs/methodology_audit.md`, `docs/hoteling_model.md`, `docs/port_ops_model.md`).
- Reference databases and citation maps (e.g., `docs/references.bib`, `docs/tf_literature_citation_map.md`).
- Specific research prompts or data verification requests from the user.

## 4. Step-by-Step Workflow
1. **Context Alignment**: Locate and inspect the relevant academic drafts, calculations, and data inventories in the `docs/` and `modules/` directories.
2. **Assumption & Data Categorization**: Classify every parameter, coefficient, and data point used in the discussion or equation into one of the following distinct categories:
   - *Observed/Measured Data* (e.g., actual recorded vessel voyages, fuel receipts, port logs).
   - *Literature Values* (e.g., EMEP/EEA emission factors, ICCT/IMO report coefficients).
   - *Project Assumptions* (e.g., specific routing parameters, average truck payloads).
   - *Fallbacks/Approximations* (e.g., average auxiliary engine load when specific data is missing).
3. **Dimensional & Equation Audit**: Before proposing any updates to text, equations, or code:
   - Perform a formal dimensional analysis (e.g., ensuring emissions values match units like $\text{g CO}_2\text{/t}\cdot\text{km}$ or $\text{kg CO}_{2\text{eq}}\text{/TEU}$).
   - Explicitly define the system boundary: Tank-to-Wheel (TTW), Well-to-Tank (WTT), or Well-to-Wheel (WTW).
4. **Consistency Verification**: Cross-reference any updated calculation or statement against the existing methodologies in the repository (e.g., in `modules/` or `docs/`). Ensure changes do not introduce structural contradictions.
5. **Language Rule**: Match the target document language. For this project, academic report text is likely Portuguese unless the target file or user request is in English.
6. **Drafting or Review**: Revise the target text or model description, ensuring academic tone (passive voice where appropriate, precise terms, clear limitations).
7. **Self-Correction & Checklist Validation**: For substantive tasks, run through the Academic Validation Checklist. Reject any draft or output that fails these checks.

## 5. Academic Validation Checklist
Validate all drafted or reviewed text against the following criteria:
- [ ] **Data Category Separability**: Are observed/measured data, literature parameters, project-specific assumptions, and fallback values clearly distinguished?
- [ ] **Methodological Defensibility**: If an examiner questions a parameter, is it traceable to an authoritative source or justified by an engineering model?
- [ ] **Emission Classifications**: Are emissions clearly specified as $\text{CO}_2$ vs. $\text{CO}_{2\text{eq}}$ (greenhouse gases)? Are the boundaries (TTW, WTT, WTW) explicitly defined?
- [ ] **Modal Comparison Defensibility**: Does the road vs. cabotage comparison use equitable system boundaries? (e.g., does it account for pre/post-carriage road legs, port handling emissions, and detours/circuity factors for maritime routes?)
- [ ] **Dimensional Integrity**: Are all equations dimensionally consistent? Are all units explicitly stated next to every constant, variable, or result?
- [ ] **Uncertainty & Limitations**: Are the model's limitations, data constraints, and assumptions explicitly disclosed?

## 6. Source and Citation Rules
- **No Inventions**: Never invent citations, authors, papers, or regulatory claims.
- **Authoritative Standards**: Align maritime emissions factors with recognized international guidelines (e.g., EMEP/EEA Air Pollutant Emission Inventory Guidebook, IMO Greenhouse Gas Studies, GLEC Framework) or Brazilian national databases (e.g., PBGHG, ANTAQ, EPL/LabTrans).
- **Citation Traceability**: Use the existing BibTeX keys from `docs/references.bib` when referencing papers.
- **BibTeX Modification**: If a new paper is referenced, the agent should recommend the addition rather than modifying files directly. Only modify `docs/references.bib` when the user explicitly asks for bibliography maintenance or the current task clearly requires it.
- **Traceability Chain**: Provide a clear explanation of how any input data was transformed, filtered, or aggregated from the source files (e.g., from raw xlsx tables or papers).

## 7. Methodology Consistency Rules
- **Constant Reconciliation**: Any maritime or road fuel consumption calculations must use energy densities and carbon factors consistent with standard references (e.g., ANP - Agência Nacional do Petróleo for Brazil, or IMO/GHG factors).
- **Vessel Class Specificity**: Always distinguish vessel types and sizes (e.g., Panamax, Feedership, Handysize) when discussing fuel consumption rates and efficiencies.
- **Port Operations Integration**: Account for terminal-side activities (e.g., RTG - Rubber Tyred Gantry cranes, TT - Terminal Tractors) when calculating port leg emissions, separating them clearly from seagoing transport legs.
- **Road Circuity and Maritime Detour Factors**: Explicitly state the route circuity factors (actual distance divided by great-circle distance) used for both road and sea transport.

## 8. Skill Boundaries & Calculation Auditing
- **Conceptual & Academic Focus**: This skill focuses on reviewing calculation methodology, theoretical assumptions, and dimensional consistency at an academic/conceptual level.
- **Detailed Auditing**: Detailed numerical code audits and database validation belong to a dedicated calculation-auditor workflow (when available) rather than this skill.

## 9. Red Flags / Things to Reject
- **Lumping CO2 and CO2eq**: Treating $\text{CO}_2$ and $\text{CO}_{2\text{eq}}$ as interchangeable terms.
- **Undefined System Boundaries**: Discussing decarbonization or modal shift without defining whether the analysis covers only TTW (direct combustion) or full WTW (including fuel production/transportation).
- **Asymmetric Comparisons**: Comparing door-to-door road transport against port-to-port maritime cabotage without accounting for road first/last mile and port operations.
- **Undocumented Parameters**: Introducing new numeric parameters (e.g., cargo loading factors, fuel consumption rates) without an explicit literature citation or a clearly documented engineering derivation.
- **Oversimplified Claims**: Making sweeping claims about maritime cabotage being "always cleaner" or "always cheaper" without showing sensitivity to routing distances, vessel payloads, or port delays.

## 10. Expected Outputs
When a task is complete, the final response must contain:
1. The revised text or calculation, formatted cleanly in LaTeX or Markdown.
2. For substantive academic, methodology, calculation, or literature-review tasks:
   - An **Academic Defensibility Statement** summarizing:
     - The assumptions invoked.
     - The categories of data used (Observed vs. Literature vs. Assumptions).
     - The specific citations/sources from `docs/references.bib` or project docs.
     - The system boundary (TTW/WTT/WTW) and carbon species ($\text{CO}_2$ vs. $\text{CO}_{2\text{eq}}$).
   - The results of the **Academic Validation Checklist**.
   (For simple edits, typo fixes, or small tasks, these statement and checklist steps are optional and can be omitted.)

## 11. Non-Goals
- Inventing or proposing hypothetical alternative fuels or ship designs that are not standard/practical for current Brazilian cabotage.
- Proposing major changes to the Streamlit app's UI or backend code.
- Rewriting the entire final report draft in a single step (work must be incremental and focused).
