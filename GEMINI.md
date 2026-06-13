# GEMINI.md - CabotageLens repo instructions

Follow `AGENTS.md` for the full repository guidance.

CabotageLens is a Streamlit Cloud-oriented academic app for Brazilian freight
transport comparison:

- Streamlit orchestrates the app UI, access gate, session state, and result display.
- `modules/` contains the reusable domain logic for routing, cabotage, fuel,
  emissions, costs, persistence, data loading, and logging.
- Supabase Postgres is the only durable database backend.
- Supabase Storage is optional for archived logs and runtime data assets when
  configured.
- Local files under `data/` are useful for tracked static inputs, development
  fixtures, and deterministic generated artifacts.
- `requirements.txt` is the dependency source of truth for local development and
  Streamlit Cloud deployment.

Do not use `pyproject.toml` as the normal install, deploy, packaging, or version
management workflow. Do not update `[project].version` unless explicitly
requested. Do not require `pip install -e .` for normal usage.

Keep changes small, maintainable, Windows-friendly, Streamlit Cloud-compatible,
and consistent with the existing academic product surface. Do not introduce
Docker, Poetry, PDM, uv, background workers, queues, schedulers, new cloud
infrastructure, or extra services unless explicitly requested.

This is an academic naval engineering project. Treat methodology changes as
research work, not just app behavior:

- Prefer observed/concrete data over assumptions whenever available.
- Keep units explicit and dimensionally consistent.
- Do not invent coefficients, constants, fuel prices, emissions factors, vessel
  parameters, or methodology claims.
- Make approximations, filters, fallbacks, and data losses explicit when they
  affect interpretation.
- Preserve a citation trail in docs, comments, or metadata when practical.
- Avoid false precision in displayed results.

Use `CabotageLens` when referring to the app. Use `road-only route`,
`cabotage-assisted route`, `first-mile`, `sea leg`, and `last-mile` consistently
when discussing route components.

When handing off a commit instead of creating it directly, end the final response
with only the Conventional Commit message text. Do not include a PowerShell
assignment, `git add`, `git commit`, or any other shell commands.
