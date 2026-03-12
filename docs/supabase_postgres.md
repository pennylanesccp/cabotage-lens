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
ORS_API_KEY = "your-openrouteservice-key"
LOCATIONIQ_PAT = "your-locationiq-private-token"
SUPABASE_PROJECT_REF = "your-project-ref"
SUPABASE_DB_PASSWORD = "your-supabase-password"
SUPABASE_DB_PORT = 5432
```

CLI scripts and the Streamlit app both load `.streamlit/secrets.toml` automatically. Environment variables are also accepted as a fallback when a secret is not set.

The runtime builds the Postgres DSN from the component secrets, so passwords do not need manual URL-encoding. By default it derives the direct host as `db.<project-ref>.supabase.co`, uses database `postgres`, user `postgres`, and `sslmode=require`.

Optional overrides:

```toml
# Needed only when you want to override the derived direct host, for example a pooler host.
# SUPABASE_DB_HOST = "aws-0-us-east-1.pooler.supabase.com"
# SUPABASE_DB_USER = "postgres.your-project-ref"
# SUPABASE_DB_NAME = "postgres"
# SUPABASE_DB_SSLMODE = "require"
```

If you set `SUPABASE_DB_PORT = 6543`, also set `SUPABASE_DB_HOST` explicitly because the pooler hostname cannot be derived from the project ref alone.

SQLite is no longer part of the shipped app and CLI pipeline. The only remaining SQLite usage is in one-off maintenance tools under `legacy/sqlite/`.

Maintenance-only example:

```toml
CARBON_DB_PATH = "data/processed/database/carbon_footprint.sqlite"
```

`CARBON_DB_PATH` is only used by one-off SQLite maintenance tools.

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
.\venv\Scripts\python.exe .\legacy\sqlite\migrate_sqlite_to_supabase.py --dry-run --log-level INFO
```

Run the migration:

```powershell
.\venv\Scripts\python.exe .\legacy\sqlite\migrate_sqlite_to_supabase.py --log-level INFO
```

Optional flags:

- `--sqlite-path` points to a non-default SQLite file.
- `--table` limits migration to one or more source tables.
- `--no-include-analysis-tables` skips legacy single-run analytical tables.

## Notes

- The ORS client now keeps only an in-process response cache. The shipped runtime no longer writes a separate local SQLite HTTP cache file.
- Route-cache lookups and writes now use the configured backend automatically.
- Bulk reruns still recompute analytical outputs while reusing cached road distances when available.
- The Streamlit heatmap page reads only completed Supabase batch runs and uses the immutable `bulk_evaluation_run_results` rows for map rendering.
