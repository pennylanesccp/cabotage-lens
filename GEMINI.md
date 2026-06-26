# GEMINI.md - CabotageLens repo instructions (Literature Audit Branch)

Follow `AGENTS.md` for the full repository guidance.

CabotageLens is a Streamlit Cloud-oriented academic app for Brazilian freight
transport comparison.

## Branch Workflow: Literature Audit (`lit/paper-intersections`)

This branch is dedicated to literature review and audit work comparing local reference papers against the current methodology, validation documents, assumptions, and thesis structure.

### Scope of Work and Directory Restrictions

- **Editing is restricted to**: Only files under `docs/literature_audit/`.
- **Exception for initialization**: Updating `GEMINI.md` itself is allowed during initialization.
- **Do not edit anything else**. The assistant must not edit source code, data files, existing methodology docs, validation docs, config, or assets outside of `docs/literature_audit/`.

### Read Permissions

The assistant may freely read the rest of the repository for context, including:
- `docs/`
- `docs/validation/`
- `docs/references.bib`
- `docs/references_renames.md`
- Local-only files under `docs/references/` (if present locally)
- Source code, data files, and configuration files (for understanding context only)

### Important Constraints for Literature Audit

- **Do not modify source code** or database schemas.
- **Do not modify data/model files**.
- **Do not modify metadata or config files**: Do not edit `README.md`, `AGENTS.md`, `.gitignore`, `requirements.txt`, `pyproject.toml`, app files under `app/`, scripts under `scripts/`, modules under `modules/`, or tests under `tests/`.
- **Do not edit existing validation results** or TF methodology documents directly.
- **Do not edit existing validation docs directly**.
- **Do not commit sensitive/local-only files**: Never commit PDFs, private workbooks, `.env`, `.streamlit/secrets.toml`, tokens, credentials, or local caches.
- **Local-Only Files**: Reference PDFs and private benchmark workbooks under `docs/references/` are local-only and must remain ignored by Git.
- **Outputs**: Future outputs should be documentation-only files under `docs/literature_audit/`.
- **Purpose of Audit**: Identify intersections between local reference papers and the thesis, citation gaps, methodology caveats, recommended inclusions, and possible future changes, but do not apply those changes to code or existing docs directly.
- **Units and Dimensions**: Preserve units and dimensional consistency.
- **Emissions Definitions**: Distinguish Tank-to-Wake (TTW), Well-to-Wake (WTW), Life Cycle Assessment (LCA), CO2, and CO2e. Do not conflate these.
- **Academic Rigor**: Do not invent coefficients, emissions factors, fuel prices, vessel parameters, route distances, paper claims, or methodology claims.
- **Defensibility**: Keep outputs defensible for a naval engineering academic project.

When handing off a commit instead of creating it directly, end the final response
with only the Conventional Commit message text. Do not include a PowerShell
assignment, `git add`, `git commit`, or any other shell commands.

