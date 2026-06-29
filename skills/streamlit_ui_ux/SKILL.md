---
name: streamlit_ui_ux
description: UI/UX layout, components, data visualization, and academic transparency rules for Streamlit application pages.
---

# Streamlit UI/UX Design and Implementation Skill

## 1. Purpose
This skill provides a structured framework for agents working on the user interface (UI) and user experience (UX) of the CabotageLens application. It ensures that the app presents complex multimodal logistics, cost, and emissions data clearly and dynamically without compromising academic rigor, hiding key methodology assumptions, or omitting unit representations.

## 2. When to Use
Trigger this skill when:
- Designing, updating, or reviewing Streamlit application pages or layouts (e.g., inside `app/` or UI components).
- Formatting result cards, tables, metrics, chart figures, or geospatial maps.
- Adjusting user input controls (e.g., input sliders, select boxes, text inputs, upload parameters).
- Implementing tooltips, helper text, system warnings, error banners, or methodology disclosure notes.
- Optimizing layouts for both desktop and mobile responsiveness.

## 3. Inputs Expected
The agent expects or must locate:
- Streamlit application scripts and layouts (e.g., in `app/`).
- Methodology documentation files (e.g., in `docs/`) to align display descriptions with underlying mathematical models.
- Specific UI/UX feature requests, layout specs, or feedback from the user.

## 4. Step-by-Step Workflow
1. **Analyze Presentation Context**: Inspect the page layout and target UI components under `app/`.
2. **Review Academic Underpinnings**: Ensure you understand the variables, emissions boundaries, and units of the calculated data to display.
3. **Formulate UI Layout**: Plan the hierarchy of inputs, metrics, tables, and visualization cards. Use tooltips and methodology callouts to explain key assumptions.
4. **Implement Streamlit Components**: Code the layouts using modern Streamlit APIs. Adhere to container widths, caching, and state preservation.
5. **Apply Data Visualization Rules**: Build charts, maps, and tables containing explicit units, labels, and clear comparisons.
6. **Incorporate Error & Empty States**: Add try-except structures around components that depend on external resources, providing clean fallback messages.
7. **Perform Validation**: Run the Validation Checklist to confirm accessibility, usability, and academic transparency.

## 5. Repository/UI Inspection Rules
- **No Unused Packages**: Do not add unnecessary frontend dependencies or third-party Streamlit custom component wrappers (like custom JS/HTML objects) unless they are already listed in `requirements.txt` or strictly requested.
- **Maintain App Structure**: Keep UI state orchestration inside `app/` and business calculations or service clients in `modules/`. Avoid calculations directly in Streamlit UI callbacks.

## 6. UI Layout Principles
- **Aesthetic Excellence**: Follow modern web design best practices (harmonious colors, consistent dark/light styling, proper alignment, clear typography).
- **Clean Structure**: Present information with a clear visual hierarchy. Use headers (`st.subheader`), columns (`st.columns`), tabs (`st.tabs`), and expanders (`st.expander`) logically to avoid cluttering.
- **Academic Context**: Place methodology highlights or assumptions near the results they affect. Use info alerts (`st.info`) or callout banners to contextualize values.

## 7. Streamlit Implementation Rules
- **Streamlit Version Compliance**: Write code compatible with Streamlit Community Cloud.
- **API Guidelines**:
  - Prefer current Streamlit APIs over deprecated functions.
  - When handling parameters like `use_container_width`, do not apply a blanket automatic replacement. Future agents must inspect the project's pinned Streamlit version (e.g. in `requirements.txt`) and specific API documentation before replacing deprecated parameters. Prefer modern Streamlit APIs, such as setting `width="stretch"` where supported, ensuring compatibility is not broken.
- **Session State Hygiene**: Preserve user inputs across page reruns by caching keys and setting explicit default state objects when necessary.
- **Performance Caching**: Ensure expensive operations (e.g., route fetching, file parsing) are cached so that normal page interactions do not trigger sluggish page runs.

## 8. Academic Transparency Rules
- **Expose Assumptions**: Ensure that pre-carriage, on-carriage, port delays, vessel hotelling load factors, cargo handling, and routing detours are disclosed clearly in the UI.
- **Explicit Boundaries**: Clearly state the emission boundaries: Well-to-Tank (WTT), Tank-to-Wake (TTW for maritime) / Tank-to-Wheel (TTW for road), or Well-to-Wake (WTW for maritime) / Well-to-Wheel (WTW for road). Never lump these together.
- **Species Clarity**: Distinguish clearly between $\text{CO}_2$ (carbon dioxide) and $\text{CO}_{2\text{eq}}$ (greenhouse gases including methane, etc.).
- **Uncertainty & Fallbacks**: If default fallbacks (e.g., routing approximations or default fuel constants) are active due to missing inputs, display an warning banner or text (e.g., `st.warning`) explaining the approximation.

## 9. Data Visualization Rules
- **Unit and Scale Labels**: Every chart axis, map layer, table column, and metric card must display its unit (e.g., $\text{t CO}_{2\text{eq}}$, $\text{km}$, $\text{g/t}\cdot\text{km}$, $\text{R\$}$, $\text{USD}$).
- **Equitable Visual Comparisons**: Do not visually compare road and cabotage on the same chart unless their system boundaries are equivalent or the structural differences are clearly annotated.
- **No Biased Generalizations**: Do not imply in the UI that cabotage is "always cleaner" or "always cheaper". Present outputs as route-, payload-, and assumption-dependent.
- **Academic Annotations**: Prefer clear titles, captions, and footnote notes explaining data source limits over flashy visual animations that add no scientific value.

## 10. Form/Input Rules
- **Sensible Ranges**: Slide controls, numbers, and inputs must have validated bounds to prevent division-by-zero or physical impossibilities (e.g., negative payloads, speeds above ship capacity).
- **Tooltip Assistance**: Provide explanatory tooltips (`help="..."` parameter in Streamlit widgets) for non-obvious logistics parameters (like circuity factors, specific fuel consumption, and cargo loading rates).

## 11. Results Presentation Rules
- **Avoid Misleading Precision**: Round output values to reflect the quality of the inputs. Do not show emissions with decimal precision unless the underlying data justifies it.
- **Multi-scenario Comparison**: Use tab layouts or side-by-side metric layouts to present baseline (road-only) vs. alternative (multimodal cabotage) scenarios clearly.

## 12. Error and Empty-State Rules
- **Empty States**: If no route has been computed or coordinates are not resolved, display a clean, neutral screen explaining the missing input rather than an empty dashboard or raw python trace.
- **Friendly Errors**: Wrap geocoding and database persistence calls in user-recoverable messages (e.g., `st.error("Serviço de rotas temporariamente indisponível. Por favor, tente novamente.")`).

## 13. Mobile/Responsiveness Considerations
- **Responsive Elements**: Avoid hardcoding pixel widths for charts, tables, or frames. Ensure elements adjust automatically to smaller mobile screens.
- **Column Wrapping**: Be mindful of column layouts. Columns should adapt gracefully without squishing texts or making numbers unreadable on small screens.

## 14. Validation Checklist
Verify the UI changes against the following:
- [ ] **Labels with Units**: Are all output labels, table columns, metric cards, and charts annotated with correct units?
- [ ] **Boundary Clarifications**: Are the emissions scopes (TTW/WTT/WTW, using Tank-to-Wake/Well-to-Wake for maritime and Tank-to-Wheel/Well-to-Wheel for road) and carbon species ($\text{CO}_2/\text{CO}_{2\text{eq}}$) explicitly stated?
- [ ] **Streamlit Cloud Ready**: Is the page free of unsupported libraries, and are any Streamlit API parameter updates (e.g. `use_container_width` vs. `width="stretch"`) verified against the pinned Streamlit version in `requirements.txt`?
- [ ] **Empty States**: Does the app show clean instructions if inputs are missing?
- [ ] **Error Boundaries**: Are network failures caught and surfaced as friendly banners rather than traceback screens?
- [ ] **Responsiveness**: Do layout grids and columns render cleanly on standard desktop and mobile viewports?

## 15. Red Flags / Things to Reject
- **Lumping Boundaries**: Mixing TTW and WTW outputs without clearly labeling them.
- **Hiding Assumptions**: Presenting route emissions or costs without displaying the underlying variables (cargo weight, detours, pre/on-carriage distances).
- **Misleading Precision**: Displaying metrics with excessive decimal values that imply false mathematical precision.
- **Raw Tracebacks**: Showing raw Python exception screens directly to the user instead of handling exceptions defensively.
- **Overdesigned Visuals**: Adding visual clutter, unnecessary javascript bindings, or custom theme modifications that violate academic styling conventions.

## 16. Expected Outputs
Depending on the size of the task, the agent must produce:

- **For Small UI Tasks / Tweaks**:
  - A concise implementation summary listing layout changes and verification steps.

- **For Substantive UI/UX Changes**:
  1. **UI Problem Diagnosed**: Rationale for the design adjustment.
  2. **Files/Components Inspected**: List of relative paths reviewed.
  3. **User-Facing Behavior Changed**: Explanation of what the user sees and interacts with.
  4. **Methodology Transparency Preserved**: Verification that units, boundaries, and limitations remain explicit.
  5. **Validation/Manual Checks**: Details of how layout, responsive wrapping, and error states were validated.
  6. **Remaining Limitations**: Any outstanding UX constraints.

## 17. Language Rule
- Match the user request language.
- User-facing app text (labels, warnings, text fields, UI buttons) should default to Portuguese unless the surrounding app page is explicitly designed in English.
- Standard technical abbreviations (e.g., $\text{CO}_2$, $\text{CO}_{2\text{eq}}$, $\text{TTW}$ [Tank-to-Wake/Wheel], $\text{WTT}$ [Well-to-Tank], $\text{WTW}$ [Well-to-Wake/Wheel], $\text{TEU}$, $\text{t}\cdot\text{km}$) can remain in their standard forms but must be explained in tooltips or legend notes when context warrants (ensuring mode-appropriate terminology: Wake for maritime, Wheel for road).

## 18. Non-Goals
- Modifying underlying calculation formulas or database persistence structures.
- Auditing emissions logic or citing academic papers (which are handled by the academic research and calculation auditor skills).
