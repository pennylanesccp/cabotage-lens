# GEMINI.md - CabotageLens repo instructions

Follow `AGENTS.md` for the full repository guidance. This file is a compact handoff for Gemini Code Assist and other coding agents working on CabotageLens.

CabotageLens is a Streamlit Cloud-oriented academic app for Brazilian freight transport comparison. It compares road-only routes with road-cabotage-road alternatives for containerized cargo, with emphasis on emissions, cost estimates, system boundary, data provenance, and defensible validation for the PNV3510 final project.

## General Work Scope

- Treat the user's current request as the source of truth for the scope of each branch or issue.
- Do not assume branch-specific restrictions unless the user explicitly gives them.
- Literature-audit files under `docs/literature_audit/` are evidence and planning inputs; do not automatically apply their recommendations as model changes.
- Keep changes small and targeted unless the user explicitly requests a broader refactor.

## Repository Guardrails

- Keep the app deployable on Streamlit Community Cloud through `requirements.txt`.
- Keep secrets in Streamlit secrets or environment variables; never commit `.streamlit/secrets.toml`, `.env`, tokens, credentials, or private keys.
- Do not commit local-only reference PDFs, private workbooks, caches, or files under `docs/references/`.
- Do not alter historical validation results as if they were rerun. Add new validation batches, correction notes, or follow-up records instead.
- Avoid broad source-code, schema, data, or configuration changes when documentation or a narrow UI wording change is enough.

## Academic and Methodology Guardrails

- Preserve units and dimensional consistency in calculations, docs, UI labels, and exported outputs.
- Do not invent coefficients, emissions factors, fuel prices, vessel parameters, route distances, costs, or paper claims.
- Prefer observed or concrete data over assumptions. When fallbacks are required, preserve their provenance and make their interpretive limits visible.
- Clearly distinguish:
  - Tank-to-Wake / Tank-to-Wheel (TTW) operational emissions
  - Well-to-Wake (WTW) emissions
  - Life Cycle Assessment (LCA)
  - CO2 and CO2e
- Do not substitute WTW, LCA, CO2, or CO2e values into a TTW model without an explicit boundary change, justification, and validation/sensitivity path.
- Cost outputs should be described according to their actual boundary. Do not present fuel or operational proxies as complete commercial freight rates unless the model includes the required commercial cost components.

## Validation and Batch Records

- Preserve Batch 001 as a historical validation record.
- Batch 001B and later validation work should address known distance fallback, same-port, service-plausibility, override, and provenance issues without rewriting old results.
- For route-distance fixes, preserve the source of each maritime distance: SeaMatrix, haversine fallback, manual override, bounded estimate, or external reference.
- For cabotage-inappropriate cases, such as same-port or unserved-port pairs, prefer explicit warnings or validation classifications over silent acceptance.

## Literature-Audit Follow-up

When a task uses `docs/literature_audit/`:

- Read the audit as a source map, not as an instruction to change all model factors.
- Classify findings into code changes, documentation changes, limitations/future work, and non-actions before editing calculations.
- Treat hoteling/port-operation papers that remain pending as incomplete evidence until their notes are fully audited.
- Keep final outputs defensible for a naval engineering academic project.
