# carbon-footprint

Multimodal freight comparison for Brazil, focused on road-only versus cabotage-assisted scenarios.

The current architecture is intentionally simple:

- Supabase Postgres is the only durable database.
- Supabase Storage is the optional log archive sink.
- Runtime logs go to stdout/stderr by default.
- The repository contains no embedded file-database persistence.

## What the project does

For a given origin, destination, and cargo profile, the toolkit:

1. Resolves the endpoints to coordinates.
2. Chooses the nearest origin and destination ports.
3. Builds the direct-road, first-mile, sea, and last-mile legs.
4. Estimates fuel, emissions, and energy-related cost for each leg.
5. Persists reusable route and scenario data in Supabase Postgres.

## Repository layout

- `app/` Streamlit UI
- `scripts/` CLI entrypoints
- `modules/` domain logic, routing, persistence, and logging
- `data/` tracked static inputs and processed non-database artifacts
- `supabase/migrations/` SQL migrations for the Postgres schema
- `docs/` supporting architecture and methodology notes
- `tests/` unit tests

## Persistence model

Supabase Postgres stores:

- road route cache rows
- cached place points
- single-scenario analysis tables
- bulk comparison rows
- bulk run metadata
- heatmap-ready run result rows

Supabase Storage optionally stores:

- compressed JSONL log archives under `logs/{environment}/{yyyy}/{mm}/{dd}/{run_id}.jsonl.gz`

Runtime logs are not written to a local persistent file by default.

## Configuration

Required:

```toml
ORS_API_KEY = "your-openrouteservice-key"
SUPABASE_DB_URL = "postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require"
```

Optional:

```toml
LOCATIONIQ_PAT = "your-locationiq-private-token"
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
# SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
SUPABASE_STORAGE_LOGS_BUCKET = "carbon-logs"
LOG_LEVEL = "INFO"
LOG_ARCHIVE_ENABLED = false
```

Use `.streamlit/example_secrets.toml` as the local template.

## Install

```powershell
python -m venv venv
.\venv\Scripts\pip.exe install -e .
```

## Run the Streamlit app

```powershell
.\run_streamlit.ps1
```

The app reads `.streamlit/secrets.toml`, connects to Supabase Postgres, and keeps runtime logs on stdout/stderr. If `LOG_ARCHIVE_ENABLED=true` and Storage credentials are configured, it also archives compressed JSONL logs to Supabase Storage.

## Run the CLIs

Single comparison:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_single.py `
  --origin "Sao Paulo, SP" `
  --destiny "Manaus, AM" `
  --cargo 30
```

Bulk comparison:

```powershell
.\venv\Scripts\python.exe .\scripts\compare_bulk.py `
  --origin "Pelotas, RS" `
  --dests-file .\data\processed\destinies\city_dests_over50k.txt `
  --cargo 30
```

## Logging

- Console output is always enabled.
- `LOG_LEVEL` controls verbosity.
- `LOG_ARCHIVE_ENABLED=true` enables Supabase Storage archival.
- Archived log entries include timestamp, level, module, message, and any bound run or scenario identifiers.

## Migrations

Apply these SQL files to Supabase:

- `supabase/migrations/20260309_000001_carbon_footprint_core.sql`
- `supabase/migrations/20260310_000002_bulk_heatmap_runs.sql`
- `supabase/migrations/20260312_000003_bulk_pipeline_perf.sql`

## Tests

This repository now uses unit tests that mock the Postgres and Storage boundaries instead of relying on local file-database fixtures.

## Notes

- The route cache is durable and shared through Postgres.
- The heatmap page reads and writes only the Supabase-backed bulk tables.
- There is no local database fallback.
