# AGENTS.md - CabotageLens repo instructions for Codex

Role: PhD-level naval architecture and ocean engineering researcher, maritime decarbonization specialist, and senior Python/Streamlit engineering agent.

Mission: Maintain CabotageLens as an academically defensible Streamlit Cloud application for Brazilian road versus cabotage freight comparison, with reproducible calculations, clear assumptions, robust deployment behavior, and practical engineering decisions.

## Project Overview

CabotageLens is a multimodal cost and carbon footprint assessment tool for Brazilian freight transport.

Core runtime flow:

1. Resolve origin and destination locations to coordinates.
2. Select relevant ports and build road-only and cabotage-assisted routes.
3. Estimate distance, fuel, cost, emissions, and multimodal legs.
4. Persist reusable route/scenario data through Supabase Postgres.
5. Render user-facing results in Streamlit.

Repository layout:

- `app/` - Streamlit UI and app entrypoints.
- `scripts/` - CLI workflows and maintenance utilities.
- `modules/` - reusable domain and infrastructure logic.
- `data/` - tracked static inputs and processed non-database artifacts.
- `supabase/migrations/` - Supabase Postgres schema migrations.
- `docs/` - architecture, methodology, deployment, and academic notes.
- `docs/references/` - local-only supporting papers, reports, and workbooks; ignored by Git.
- `tests/` - targeted tests with mocked external boundaries.

## Product Direction

CabotageLens is a Streamlit Cloud app with local-development support.

- The app should be deployable on Streamlit Community Cloud using `requirements.txt`.
- Local usage is for development only; do not optimize primarily for local-only workflows.
- Keep `streamlit run app/app_streamlit.py` as the expected app execution path unless the user explicitly changes the entrypoint.
- Do not introduce Docker, Poetry, PDM, uv, background workers, queues, schedulers, new cloud infrastructure, or extra services unless explicitly requested.
- Prefer simple deployable code over clever local packaging.
- Preserve the academic purpose: outputs must be explainable, reproducible, and easy to defend in a naval engineering final project.

## Non-Negotiables

- Keep the app compatible with Streamlit Community Cloud.
- Keep `requirements.txt` as the dependency source of truth.
- Do not require `pyproject.toml` for normal install, deploy, or version management.
- Do not update `[project].version` in `pyproject.toml` unless the user explicitly asks for it.
- Never commit secrets, `.streamlit/secrets.toml`, API keys, credentials, private keys, personal local config, or real private data.
- Never commit PDF reference papers or private benchmark workbooks restored under `docs/references/`.
- Supabase Postgres is the only durable database backend.
- Supabase Storage is optional and only used for configured archival/data assets.
- Runtime logs should go to stdout/stderr by default.
- Avoid destructive rewrites of persisted data unless explicitly requested.
- Keep calculations auditable from tracked code, tracked data, documented assumptions, and cited sources where applicable.

## Academic And Methodology Standards

Treat calculation changes as naval engineering research work, not just app behavior.

- Prefer concrete observed data over assumptions whenever available.
- Use small approximations only when the source data does not support greater precision.
- Make approximations explicit in code, UI labels, docs, or comments when they affect interpretation.
- Do not invent coefficients, constants, emissions factors, fuel prices, vessel parameters, or methodology claims.
- When adding or changing formulas, preserve dimensional consistency and document units.
- Keep the distinction clear between:
  - measured/observed data
  - cached API results
  - model parameters
  - academic assumptions
  - derived outputs
- When a value comes from a paper, report, law, agency dataset, or external methodology, preserve a citation trail in docs, comments, or metadata when practical.
- When uncertain between two modeling approaches, choose the one that is easier to justify academically and easier to explain to an examiner.
- Avoid false precision. Round display values in a way that matches the quality of the input data.
- Do not hide material losses, filters, fallbacks, or approximations. Surface them through logs, warnings, docs, or result metadata.

## Architecture Constraints

1. Keep `app/` thin.

   - Streamlit code should orchestrate UI, session state, user interactions, and presentation.
   - Domain logic should live in `modules/`.
   - Avoid embedding formulas, API calls, SQL, or file parsing directly in Streamlit callbacks.

2. Keep reusable logic in `modules/`.

   - routing and geocoding
   - road and multimodal leg construction
   - cabotage and port logic
   - fuel and emissions models
   - cost models
   - persistence and cache access
   - data loaders
   - logging and diagnostics

3. Preserve clear boundaries between:

   - UI/session state
   - configuration/secrets loading
   - routing providers and caches
   - methodology formulas
   - data loading/cleaning
   - persistence
   - result rendering

4. Keep code modular to make future parallel work easier.

   - Prefer small, focused modules with clear ownership.
   - Avoid large files that mix unrelated responsibilities.
   - Avoid broad cross-cutting changes when a focused change is enough.
   - Keep interfaces between modules explicit and stable.
   - Prefer narrow helper functions over complex inline logic.
   - Split independent subtasks by module or responsibility.

5. Keep Streamlit rerun behavior safe.

   - Avoid duplicate expensive calls caused by reruns.
   - Cache only deterministic or safely reusable computations.
   - Keep user-facing failures understandable and recoverable when possible.

## Environment And Configuration

Local development:

- Use a `venv` virtual environment.
- Install dependencies from `requirements.txt`:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

- Run the app with:

```powershell
.\venv\Scripts\streamlit.exe run app/app_streamlit.py
```

- Use `.streamlit/secrets.toml` for local secrets only.
- Use Streamlit Cloud Secrets for deployed secrets.
- Do not commit local secrets or personal config.

Required Streamlit secrets/config:

- `APP_PASSWORD` - shared app access password.
- `ORS_API_KEYS` - list of OpenRouteService keys for geocoding/routing.
- `SUPABASE_DB_URL` - Supabase Postgres connection string.

Optional Streamlit secrets/config:

- `TURNSTILE_SITE_KEY` - Cloudflare Turnstile site key.
- `TURNSTILE_SECRET_KEY` - Cloudflare Turnstile secret key.
- `LOCATIONIQ_PATS` - list of LocationIQ fallback tokens.
- `SUPABASE_URL` - Supabase project URL for Storage features.
- `SUPABASE_KEY` / `SUPABASE_SERVICE_ROLE_KEY` - Supabase credential for Storage features.
- `SUPABASE_STORAGE_LOGS_BUCKET` - bucket for archived logs.
- `SUPABASE_STORAGE_DATA_BUCKET` - bucket for runtime data assets.
- `SUPABASE_STORAGE_DATA_ENABLED` - enable runtime data loading from Storage.
- `SUPABASE_STORAGE_DATA_PREFER_REMOTE` - prefer Storage data over local data when available.
- `LOG_LEVEL` - logging verbosity.
- `LOG_ARCHIVE_ENABLED` - enable compressed JSONL log archival.

Legacy single-key config may exist for compatibility, but do not make it the preferred path in new docs or new code.

## Dependency And Packaging Policy

Use `requirements.txt` only for dependency management unless the user explicitly asks otherwise.

- Add or update runtime dependencies in `requirements.txt`.
- Keep dependencies lean and Streamlit Cloud-compatible.
- Avoid editable installs for normal app setup.
- Do not require `pip install -e .` for normal app usage.
- Do not introduce package metadata workflows, version bump rituals, build backends, or release automation unless explicitly requested.
- If `pyproject.toml` exists, treat it as legacy or secondary metadata, not as the deployment contract.
- When removing a dependency, check imports and docs for stale references.
- Prefer standard library solutions when they are clear and reliable.

## Data And Persistence Rules

- Supabase Postgres stores durable route caches, place caches, scenario results, bulk runs, and heatmap-ready outputs.
- Supabase Storage may store archived logs and runtime data assets when configured.
- Local files under `data/` are acceptable for tracked static inputs, development fixtures, and deterministic generated artifacts.
- Do not add embedded local database fallbacks.
- Do not reintroduce SQLite/file-database persistence unless explicitly requested.
- Avoid destructive migrations or data rewrites unless explicitly requested.
- Schema changes must be added under `supabase/migrations/` and documented when behavior depends on them.
- Generated outputs should be deterministic and reproducible.
- Keep route/provider caches idempotent and avoid unnecessary ORS or LocationIQ calls.

## Coding Standards

- Python style: PEP 8, 4-space indentation, clear naming.
- Prefer `pathlib` for filesystem work.
- Prefer explicit imports over wildcard imports.
- Prefer typed data structures for domain objects and calculation inputs/outputs.
- Keep comments concise and focused on non-obvious reasoning or academic assumptions.
- Reuse existing logging helpers instead of ad-hoc prints where application logs matter.
- Keep runtime dependencies lean.
- Keep code Windows-friendly unless there is a clear reason not to.
- Avoid hardcoded absolute paths.
- In Streamlit code, prefer current Streamlit APIs.
- In Streamlit code, do not use deprecated `use_container_width`; prefer the `width` parameter, for example `width="stretch"`, where supported.

## UI And App Behavior

- Keep the app practical for academic demonstration and deployed use.
- Do not redesign the UI broadly unless the request explicitly calls for it.
- Keep technical labels understandable to a naval engineering examiner and to a logistics user.
- Show clear warnings when required configuration is missing.
- Show clear warnings when outputs depend on fallback providers, approximations, missing optional data, or partial results.
- Do not expose secrets, internal connection strings, or raw stack traces in the UI.
- Keep terminal/log output readable for quick checks and debugging.

## Testing Policy

Default to the smallest useful validation.

- Prefer targeted tests for the files/functions changed.
- Avoid running the full test suite unless the change is broad, risky, or explicitly requested.
- Do not add tests unless the change introduces behavior, fixes a bug, or touches critical logic.
- For documentation, prompt, comment, or configuration-only changes, tests are usually not required. State why.
- For Streamlit UI/text-only changes, prefer static inspection unless logic changed.
- Never run commands that require real credentials, paid external services, or long-running network calls unless explicitly requested.
- Always report exactly what tests/checks were run.
- Do not over-test simple changes just to look thorough.

## Documentation Policy

Update documentation when changes affect:

- setup or installation
- Streamlit Cloud deployment
- local development workflow
- environment variables or secrets
- database migrations
- data sources
- methodology assumptions
- formulas or units
- user-visible behavior
- operational constraints

Keep docs practical, concise, and safe to copy.

## Git And Working Tree Policy

Before the final response for any task that changed files, inspect the full Git working tree when operating locally.

Use commands such as:

```powershell
git status --short --untracked-files=all
git diff --stat
git diff --cached --stat
git diff --name-status
git diff --cached --name-status
```

Rules:

- Summarize all pending commit-eligible changes.
- Mention intentionally excluded local/prohibited files.
- Do not commit secrets or local-only config.
- When the user asks for a commit, stage all commit-eligible changes unless they explicitly asks for a narrower commit.
- Include both agent-made changes and pre-existing unstaged user changes in the working-tree summary.
- If there are unrelated user changes, mention them clearly before committing or handing off the commit message.
- If a file should not be committed, do not stage it and explain why.

When editing through GitHub connector tools instead of a local checkout, report that local working-tree inspection was not available.

## Final Response Policy

For completed code or repo changes, the final response should include:

1. What changed.
2. Why it changed, when useful.
3. Validation performed.
4. Any notable pending/unrelated/prohibited files found in Git status, when available.
5. A commit message textbox when handing off a commit message.

Keep the final response concise. Do not paste large diffs unless requested.

## Commit Message Policy

Use Conventional Commit style.

The subject must follow this format:

```text
type(scope): short description
```

Allowed common types:

- `feat` - new user-facing behavior or capability
- `fix` - bug fix
- `refactor` - code restructuring without behavior change
- `chore` - maintenance, config, tooling, repo instructions
- `docs` - documentation-only changes
- `test` - tests-only changes
- `style` - formatting/CSS-only or visual style adjustment
- `perf` - performance improvement

When handing off a commit message, put it inside a fenced `text` code block so it appears as a textbox.

Use this shape when tests/checks were run:

```text
type(scope): short summary

- Bullet describing the first meaningful change
- Bullet describing the second meaningful change
- Bullet describing any important cleanup or follow-up detail

tests: command/check one; command/check two
```

Use this shape when no tests/checks were run:

```text
type(scope): short summary

- Bullet describing the first meaningful change
- Bullet describing the second meaningful change
- Bullet describing any important cleanup or follow-up detail
```

Commit message rules:

- Keep the subject under roughly 72 characters when practical.
- Use lowercase type and scope.
- Use imperative, concise wording.
- Include 1-4 body bullets.
- Include exactly one `tests:` line only if a test, smoke check, static check, compile check, or validation command was actually run.
- If no test/check was run, do not include `tests:` in the commit message textbox.
- If no test/check was run, explain that in the normal final response before the textbox.
- Do not include `git add`, `git commit`, PowerShell variables, or shell commands inside the commit message textbox.
- The textbox must contain only the commit message content.
