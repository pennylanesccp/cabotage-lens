# Supabase Architecture

`carbon-footprint` uses Supabase Postgres as the durable transactional store and Supabase Storage for optional persisted log archives.

## Core schema

Postgres tables:

- `locations`
  Canonical location dictionary keyed by `(lat6, lon6)` using 6-decimal normalized coordinates.
- `location_aliases`
  Append-friendly alias map from normalized place text to a canonical `location_id`.
- `route_cache_entries`
  Lean road-route cache keyed by `(origin_location_id, destiny_location_id, is_hgv)`.
- `bulk_runs`
  One row per bulk execution header and selector configuration.
- `bulk_run_items`
  One row per destination result within a run, referencing canonical locations and cached routes.
- `analysis_results`
  Legacy single-comparison sink still used by `scripts/compare_single.py`.

Compatibility / transition objects:

- `bulk_run_items_enriched`
  Read-friendly view joining run headers, canonical locations, and approximation-route metadata.
- Legacy tables such as `routes`, `place_points`, `bulk_evaluation_results`, `bulk_evaluation_runs`, and `bulk_evaluation_run_results`
  These remain only as migration inputs during the transition window. New runtime writes target the normalized tables above.

## Storage layout rationale

- Coordinates are stored once in `locations`, not repeated across route and bulk tables.
- Human-entered or provider-returned labels live in `location_aliases` as optional lookup metadata.
- Route cache rows reference locations instead of embedding duplicated origin/destination text and coordinates.
- Bulk result rows reference locations and cached routes instead of duplicating origin/destination payload in every destination row.

## What lives where

Postgres:

- canonical locations and aliases
- road-route cache
- bulk run headers
- bulk destination results
- single-run comparison rows where explicitly requested

Supabase Storage:

- optional compressed JSONL log archives under `logs/{environment}/{yyyy}/{mm}/{dd}/{run_id}.jsonl.gz`

Runtime stdout/stderr:

- operational logs captured by the hosting platform

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
- `supabase/migrations/20260313_000004_normalized_location_route_bulk_schema.sql`

For existing environments, run the one-time adapter after the additive migration:

- `python calcs/migrate_normalized_cache_and_bulk.py --dry-run`
- `python calcs/migrate_normalized_cache_and_bulk.py`

## Logging behavior

- Default: human-readable logs to stdout/stderr only
- Optional: the same run is archived to Supabase Storage as compressed JSONL
- Archived entries include timestamp, level, logger/module, message, and any bound run/scenario correlation fields
