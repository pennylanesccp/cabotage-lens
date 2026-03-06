# AGENTS.md - Carbon Footprint repo instructions for Codex

Role: Senior Python logistics modeling engineer.

Mission: Maintain and evolve the carbon-footprint toolkit for road vs cabotage comparisons in Brazil, with reproducible results, clear logs, and safe data handling.

---

## Project overview

This repository is a Python project focused on multimodal freight evaluation:

- `app/` - user-facing app entrypoint and Streamlit UI package
- `scripts/` - CLI workflows (`compare_single.py`, `compare_bulk.py`)
- `modules/` - domain and infrastructure code (routing, cabotage, fuel, costs, persistence)
- `data/` - versioned inputs plus processed artifacts (including SQLite database)
- `logs/` - runtime logs
- `references/` - supporting documents and research artifacts

Core flow:

1. Resolve origin/destiny coordinates and nearest ports.
2. Compute route geometry (road-only and multimodal legs).
3. Evaluate fuel, emissions, and costs per leg.
4. Persist and reuse results through SQLite cache/tables.

---

## Non-negotiables

- SQLite is the local source of truth for cached routes and scenario outputs.
- ORS API calls must use `ORS_API_KEY` from environment variables (prefer `.env`).
- Pipeline behavior must remain idempotent where possible.
- Never commit secrets (`.env`, API keys, credentials).
- Keep calculations auditable and reproducible from tracked code + tracked data files.

---

## Architecture constraints

1. Keep `modules/` as the main logic layer; `app/` and `scripts/` should stay thin orchestrators.
2. Preserve routing cache behavior (avoid unnecessary ORS calls).
3. Prefer explicit typed data structures and clear boundaries between:
   - geometry building
   - cost/fuel/emissions evaluation
   - persistence
4. Respect existing filesystem layout and default paths under `data/processed/...`.

---

## Data and persistence rules

- Default database path:
  - `data/processed/database/carbon_footprint.sqlite`
- Keep schema updates backward-aware; if behavior depends on schema changes, document them.
- Avoid destructive data rewrites unless explicitly requested.
- When adding new derived outputs, prefer deterministic generation over ad-hoc side effects.

---

## Environment and configuration

Required variable:

- `ORS_API_KEY` - OpenRouteService key for geocoding and routing.

Optional variable:

- `CARBON_LOG_LEVEL` - logging verbosity override (`DEBUG`, `INFO`, etc.).

Local development conventions:

- Use `venv` virtual environment.
- Use `.env` for local secrets and settings.
- `.env.example` should provide safe placeholders only.

---

## Coding standards

- Python style: PEP 8, 4-space indentation, clear naming.
- Prefer small, composable functions over large monolithic logic.
- Keep comments concise and focused on non-obvious reasoning.
- Prefer `pathlib` for filesystem operations.
- Reuse `modules.infra.log_manager` for logging.
- Add dependencies only when justified; keep the runtime lean.

---

## CLI and app behavior expectations

- `scripts/` commands should be safe to rerun.
- Fail with clear diagnostics when required config is missing.
- Keep user-facing output readable for both quick checks and debugging.
- Preserve compatibility with `python app/app_streamlit.py` and direct script execution.

---

## Versioning (pyproject.toml) - REQUIRED

Whenever you make a change that affects shipped code or behavior, update `[project].version` in `pyproject.toml` using this repo's versioning scheme: `RELEASE.MAJOR.FEATURE.BUGFIX` (`x.y.z.w`).

Version slot meanings:

- `RELEASE` (`X.y.z.w`)
  - Reserved for release line changes only.
  - This repository is still on release line `1`.
  - Do not change the first slot unless the user explicitly asks for a release bump.
- `MAJOR` (`x.Y.z.w`)
  - Use for major changes in shipped behavior.
  - Use when the change is large, cross-cutting, or intentionally significant.
- `FEATURE` (`x.y.Z.w`)
  - Use for minor shipped features and user-visible enhancements that are not major changes.
- `BUGFIX` (`x.y.z.W`)
  - Use for bugfixes, small refactors, UI tweaks, and maintenance updates that affect shipped behavior.
  - This is the default bump when the change is not clearly a major change or a minor feature.

Mapping to Conventional Commits:

- `fix(...)`, `perf(...)`, `refactor(...)` -> bump `BUGFIX`
- `feat(...)` -> bump `FEATURE` by default, or `MAJOR` if the feature is substantial
- `!` in subject or `BREAKING CHANGE:` footer -> bump `MAJOR`, not `RELEASE`
- `docs(...)`, `test(...)`, `chore(...)` -> no bump unless runtime behavior changed

Notes:

- If uncertain, bump `BUGFIX`.
- Do not refer to this repo's versioning as SemVer in future edits.
- Keep mirrored version fields consistent if they exist.
- Mention version bump in commit body bullets when files changed.
- When converting an older 3-part version to this 4-part format, preserve `RELEASE` and `MAJOR`, initialize `FEATURE` to `0` unless historical feature counts are explicitly known, and carry the old trailing slot into `BUGFIX`.

---

## Git and completion requirement (MANDATORY)

When you finish any task, end your final message with a section titled exactly:

Commit message:

IMPORTANT formatting requirements:

- The entire commit message output must be in one fenced code block.
- That code block must be the last content in the final message.
- Use `-` for bullets.

Conventional Commits rules:

- Subject format: `type(scope): short imperative summary`
- Allowed types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`
- Suggested scopes for this repo: `app`, `scripts`, `modules`, `road`, `multimodal`, `fuel`, `costs`, `infra`, `db`, `data`, `deps`, `docs`

Body format (required when files changed):

- 1 to 9 bullets summarizing changes
- Final bullet must be one of:
  - `- Tests: {commands you ran}`
  - `- Tests: not run ({reason})`

Output format:

If code/files changed, output inside a fenced block:

```text
{type}({scope}): {subject}

- {change bullets}
```

If code/files did not change, no commit message block is needed.
