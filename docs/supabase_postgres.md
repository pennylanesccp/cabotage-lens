# Supabase Postgres Setup

The repository now uses Supabase Postgres as the primary persistence backend for:

- Road-distance cache (`routes`)
- Bulk evaluation outputs (`bulk_evaluation_results`)
- Completed bulk batches (`bulk_evaluation_runs`)
- Heatmap-ready batch rows (`bulk_evaluation_run_results`)
- Single-run analytical result tables (`analysis_results` and other compatible legacy result tables)

## Streamlit secrets

Set these in `.streamlit/secrets.toml` for local runs or in Streamlit Community Cloud secrets:

```toml
CARBON_DB_BACKEND = "postgres"
SUPABASE_DB_HOST = "db.your-project-ref.supabase.co"
SUPABASE_DB_PORT = 5432
SUPABASE_DB_NAME = "postgres"
SUPABASE_DB_USER = "postgres"
SUPABASE_DB_PASSWORD = "your-supabase-password"
SUPABASE_DB_SSLMODE = "require"
ORS_API_KEY = "your-openrouteservice-key"
```

CLI scripts and the Streamlit app both load `.streamlit/secrets.toml` automatically. `.env` is no longer read.

Optional legacy fallback:

```toml
CARBON_DB_PATH = "data/processed/database/carbon_footprint.sqlite"
```

`CARBON_DB_PATH` is only used when `CARBON_DB_BACKEND=sqlite` or by one-off SQLite maintenance tools.

## Schema bootstrap

Apply the SQL in:

`supabase/migrations/20260309_000001_carbon_footprint_core.sql`

and then:

`supabase/migrations/20260310_000002_bulk_heatmap_runs.sql`

You can run it in the Supabase SQL editor or through your usual Postgres migration workflow.

The application also creates missing tables on first use, but applying the SQL migration explicitly is the cleaner production path.

## One-time data migration

Inspect the source SQLite schema first:

```powershell
.\venv\Scripts\python.exe .\scripts\migrate_sqlite_to_supabase.py --dry-run --log-level INFO
```

Run the migration:

```powershell
.\venv\Scripts\python.exe .\scripts\migrate_sqlite_to_supabase.py --log-level INFO
```

Optional flags:

- `--sqlite-path` points to a non-default SQLite file.
- `--table` limits migration to one or more source tables.
- `--no-include-analysis-tables` skips legacy single-run analytical tables.

## Notes

- The raw ORS HTTP response cache under `.cache/ors_cache.sqlite` remains local and optional. It is not the primary persistence layer and is not migrated to Supabase.
- Route-cache lookups and writes now use the configured backend automatically.
- Bulk reruns still recompute analytical outputs while reusing cached road distances when available.
- The Streamlit heatmap page reads only completed Supabase batch runs and uses the immutable `bulk_evaluation_run_results` rows for map rendering.
