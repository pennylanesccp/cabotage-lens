# Supabase Architecture

`carbon-footprint` now uses Supabase only:

- Supabase Postgres stores all durable business data.
- Supabase Storage optionally stores archived log files.
- Runtime logs still go to stdout and stderr first.

## What lives where

Postgres tables:

- `routes` for cached road-leg distances and coordinates
- `place_points` for reusable geocoding results
- `analysis_results` and compatible single-run result tables
- `bulk_evaluation_results` for scenario result rows
- `bulk_evaluation_runs` for bulk run metadata
- `bulk_evaluation_run_results` for immutable per-run output rows

Supabase Storage objects:

- optional compressed JSONL log archives under `logs/{environment}/{yyyy}/{mm}/{dd}/{run_id}.jsonl.gz`

## Required configuration

Set these in `.streamlit/secrets.toml` or environment variables:

```toml
ORS_API_KEY = "your-openrouteservice-key"
SUPABASE_DB_URL = "postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require"
```

Optional geocoding fallback:

```toml
LOCATIONIQ_PAT = "your-locationiq-private-token"
```

Optional log archival:

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
# SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
SUPABASE_STORAGE_LOGS_BUCKET = "carbon-logs"
LOG_LEVEL = "INFO"
LOG_ARCHIVE_ENABLED = true
```

## Migrations

Apply:

- `supabase/migrations/20260309_000001_carbon_footprint_core.sql`
- `supabase/migrations/20260310_000002_bulk_heatmap_runs.sql`
- `supabase/migrations/20260312_000003_bulk_pipeline_perf.sql`

The runtime also creates missing tables on first use, but the SQL migrations remain the preferred deployment path.

## Logging behavior

- Default: human-readable logs to stdout/stderr only
- Optional: the same run is archived to Supabase Storage as compressed JSONL
- Archived entries include timestamp, level, logger/module, message, and any bound run/scenario correlation fields

## Removed behavior

- No embedded file-database backend
- No local cache fallback outside Supabase Postgres
- No persistent local database files
- No retired local-database migration tooling in the repository
