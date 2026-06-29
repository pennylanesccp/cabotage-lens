---
name: backend_data_engineering
description: Backend design, data models, persistence, APIs, validation, security, and deployment safety rules for the Streamlit and Supabase application.
---

# Backend and Data Engineering Skill

## 1. Purpose
This skill provides a structured framework for agents working on the CabotageLens backend architecture, data model, API integrations, database persistence (Supabase Postgres), routing/calculation services, caching, input validation, and deployment-sensitive data logic. It ensures compatibility with Streamlit Community Cloud, protects secrets, and maintains clean separation of concerns.

## 2. When to Use
Trigger this skill when:
- Modifying or creating database schemas, migrations, or data access code (e.g., in `supabase/` or db utilities).
- Modifying geocoding, routing, or external API consumption modules (e.g., OpenRouteService, LocationIQ integrations).
- Implementing data loaders, cleaning scripts, caching layers, or data persistence routes.
- Resolving environment configuration, runtime dependencies (`requirements.txt`), or Streamlit Cloud deployment errors.
- Handling input validation, error boundaries, or exceptions in the data-processing pipeline.

## 3. Inputs Expected
The agent expects or must locate:
- Application entry points and configuration files (e.g., `app/`, `.streamlit/config.toml`).
- Reusable domain modules and service integrations (e.g., `modules/` or service scripts).
- Database migration folders and schema definitions (e.g., `supabase/migrations/`).
- Dependency manifests (e.g., `requirements.txt`).
- Local environment configs/templates (e.g., `.env.example`, `.gitignore`).

## 4. Step-by-Step Workflow
1. **Repository & Dependency Inspection**: Review existing requirements, folder layouts, and imports before proposing or installing any package.
2. **Input Validation Design**: Define boundaries, formats, types, and constraints for all parameters before they are processed by calculators or stored in databases.
3. **Database Schema Alignment**: Review database migrations and schemas to ensure query compatibility and safety, avoiding destructive schema migrations.
4. **Service Integration & Caching**: Check API usage policies, quota limits, and caching strategies (e.g., `st.cache_data` or `st.cache_resource`) to prevent duplicate, expensive network calls.
5. **Academic Calculation Integration**: If the backend logic interacts with emissions, fuel, routing, cost estimation, or ports, strictly defer to academic/calculation constraints.
6. **Defensive Error Handling**: Wrap network, database, and file I/O operations in try-except blocks and define user-friendly error messages.
7. **Security Check**: Verify that no credentials, passwords, or personal configs are stored, logged, or checked in.
8. **Deployment Validation**: Confirm that runtime requirements remain lean, compatible with Streamlit Community Cloud, and fully documented in `requirements.txt`.

## 5. Repository Inspection Rules
- **No Unrelated Packaging**: Do not introduce Docker, Poetry, PDM, uv, background workers, task queues (e.g., Celery, Redis), schedulers, or local-only databases (like SQLite/DuckDB fallback) unless they are already configured in the repository.
- **Dependency Sufficiency**: Rely primarily on packages defined in `requirements.txt`. Do not add new libraries casually; any new dependency must be thoroughly justified and compatible with Streamlit Community Cloud.
- **Code Separation**: Keep `app/` (presentation, session state, UI) thin, and put reusable logic, persistence, and external service connectors inside `modules/`.

## 6. Data Model and Database Rules
- **Database Authority**: Supabase Postgres is the sole durable database backend. File persistence is only allowed under `data/` for static, tracked inputs or deterministic cache files.
- **Migration Policy**: Database changes must be written as incremental SQL migrations under `supabase/migrations/` and documented clearly. Never rewrite existing migrations destructively.
- **Robust Data Handling**: Implement explicit code handling for:
  - *Missing Data*: Provide logical defaults, fallback routing, or friendly error messages.
  - *Invalid Data*: Reject requests before they reach core calculation modules or db write pipelines.
  - *Duplicated Data*: Use database unique constraints or idempotent upserts.
  - *Stale/Partial Data*: Track expiration times, cache keys, or partial status flags.

## 7. API/Service Layer Rules
- **Idempotency & Caching**: Ensure external API calls (e.g., geocoding, routing) are cached appropriately to avoid exhausting api limits (e.g., using Supabase DB cache tables or Streamlit cache decorators).
- **Graceful Fallbacks**: When primary APIs fail (e.g., OpenRouteService limit reached), gracefully fall back to alternative configurations (e.g., LocationIQ) or display clear warnings without crashing the app.

## 8. Calculation Integration Rules
When backend data flows touch emissions, fuel, costs, routes, cabotage, port handling, or methodology:
- **Preserve Methodology**: Do not alter, modify, or "cleanup" calculation formulas, coefficients, emissions factors, or vessel parameters unless explicitly requested.
- **Preserve Units**: Maintain strict dimensional consistency and units across data transfer objects (DTOs), database columns, and API responses.
- **Traceability**: Ensure that derived calculations stored in the database or sent over APIs keep a trace of their sources (e.g., references to specific emission factor datasets or papers).
- **Separation of Concerns**: Clearly isolate data retrieval, transformation, calculation, and presentation layers. Calculations should take raw python types or structured dataclasses, and return typed calculation result objects.

## 9. Deployment Rules
- **Streamlit Community Cloud Compatibility**: Ensure the codebase builds and executes correctly under Streamlit Community Cloud using the environment described in `requirements.txt`.
- **System Portability**: Do not introduce OS-specific binaries, shell utilities, or compilers that will fail on Linux-based Streamlit Community Cloud.

## 10. Security/Secrets Rules
- **Environment and Secrets**: Load secrets exclusively via `st.secrets` in Streamlit or `os.environ` in backend modules.
- **Commit Guard**: Never commit `.streamlit/secrets.toml`, `.env`, private keys, API tokens, or real user credentials. Ensure these are listed in `.gitignore`.

## 11. Validation Checklist
Verify the backend code against this checklist:
- [ ] **Streamlit Cloud Compatible**: Is the runtime logic clean of custom OS wrappers or unsupported Python versions?
- [ ] **Requirements-Driven**: Are all new imports represented in `requirements.txt`?
- [ ] **Input Sanitization**: Are origin/destination queries, payloads, or table keys validated before processing?
- [ ] **Database Idempotency**: Are queries or writes safe from duplication? Are upserts used where applicable?
- [ ] **Secrets Integrity**: Are credentials protected and loaded securely from secrets or environment variables?
- [ ] **Error Isolation**: Do network failures (Supabase, Routing APIs) fail gracefully with a log/user-warning instead of crashing the Streamlit rerun?
- [ ] **Methodology Preservation**: Are core calculators untouched by database schema updates?

## 12. Red Flags / Things to Reject
- **Destructive SQL Migrations**: Schema alterations that drop tables or columns containing production data without explicit instructions.
- **Credentials Committing**: Hardcoding passwords, API tokens, or DB URLs anywhere in code, configuration files, or migrations.
- **Casual Package Additions**: Introducing heavy frameworks or local-packaging scripts (like Poetry) that interfere with simple Streamlit Community Cloud deployments.
- **Local DB Fallbacks**: Reintroducing SQLite, DuckDB, or pickle files as secondary local database backends instead of using Supabase Postgres.
- **Undocumented Assumptions**: Inserting calculation approximations directly inside database retrievers or API managers without documenting them in the methodology docs.
- **Ignoring API Errors**: Swallowing connection exceptions without log entries or warning banners in the UI.

## 13. Expected Outputs
When a task is complete, the final response must contain:

- **For Small Tasks / Bug Fixes**:
  - A concise implementation summary listing changes and validation/test commands.

- **For Substantive Backend/Data Changes**:
  1. **Files Inspected**: List of paths analyzed.
  2. **Files Changed**: List of paths modified, added, or deleted.
  3. **Data/Model Impact**: Summary of database schema changes, table schemas, or storage assets.
  4. **Deployment Impact**: Changes in dependencies (`requirements.txt`) or Streamlit secrets config.
  5. **Academic/Calculation Impact**: Confirmation that academic calculations and formulas were preserved.
  6. **Validation Commands**: Execution syntax for tests or manual validation checks run.

## 14. Language Rule
- Match the user request language.
- User-facing app text (labels, warning alerts, UI panels) should usually be Portuguese unless the surrounding UI is in English.
- Code identifiers, database column names, variable names, and technical comments may remain in English.

## 15. Non-Goals
- Modifying visual CSS styles, graphics, or layout patterns (which belong to a design/frontend scope).
- Rewriting calculation logic, emissions modeling coefficients, or vessel routing heuristics (handled by the calculation auditor or academic research skills).
