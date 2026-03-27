# CabotageLens: A Multimodal Cost and Carbon Footprint Assessment Tool for Brazilian Freight Transport

CabotageLens is a multimodal freight comparison toolkit for Brazil, focused on road-only versus cabotage-assisted scenarios.

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
- runtime data assets under `data/...` when the data bucket is configured

Runtime logs are not written to a local persistent file by default.

## Configuration

Required:

```toml
APP_PASSWORD = "your-shared-app-password"
ORS_API_KEYS = [
  "your-openrouteservice-key",
  "your-second-openrouteservice-key",
]
SUPABASE_DB_URL = "postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres?sslmode=require"
```

Optional:

```toml
TURNSTILE_SITE_KEY = "your-cloudflare-turnstile-site-key"
TURNSTILE_SECRET_KEY = "your-cloudflare-turnstile-secret-key"
LOCATIONIQ_PATS = [
  "your-locationiq-private-token",
  "your-second-locationiq-private-token",
]
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
# SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
SUPABASE_STORAGE_LOGS_BUCKET = "carbon-logs"
SUPABASE_STORAGE_DATA_BUCKET = "cabotage-lens"
SUPABASE_STORAGE_DATA_ENABLED = true
SUPABASE_STORAGE_DATA_PREFER_REMOTE = true
LOG_LEVEL = "INFO"
LOG_ARCHIVE_ENABLED = false
```

Legacy single-key entries are still accepted when the list is absent:

```toml
# ORS_API_KEY = "your-openrouteservice-key"
# ORS_API_KEY_2 = "your-second-openrouteservice-key"
# LOCATIONIQ_PAT = "your-locationiq-private-token"
```

Use `.streamlit/example_secrets.toml` as the local template.

## App access gate

- `APP_PASSWORD` is required for every environment. The app will stop early with a configuration error if it is missing.
- `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` are optional. If both are present, the login screen requires a successful Cloudflare Turnstile verification in addition to the shared password.
- If both Turnstile secrets are absent, the app falls back to password-only mode. This keeps local development simple while preserving the same access gate flow.
- Do not commit secrets. For local runs, store them in `.streamlit/secrets.toml`. For Streamlit Cloud, add them in the app Secrets settings.

## Install

```powershell
python -m venv venv
.\venv\Scripts\pip.exe install -e .
```

## Run CabotageLens

```powershell
.\run_streamlit.ps1
```

The app reads `.streamlit/secrets.toml`, shows the Router and Heatmap pages after the access gate succeeds, connects to Supabase Postgres, and keeps runtime logs on stdout/stderr. If `LOG_ARCHIVE_ENABLED=true` and Storage credentials are configured, it also archives compressed JSONL logs to Supabase Storage.

When `SUPABASE_STORAGE_DATA_BUCKET` is configured, runtime loaders prefer the bucket copy of processed cabotage artifacts and cache them locally under `.cache/supabase_data/`.

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

Upload `data/` to the Supabase Storage data bucket:

```powershell
.\venv\Scripts\python.exe .\scripts\sync_data_to_supabase_storage.py `
  --bucket cabotage-lens `
  --dry-run
```

The uploader preserves the `data/...` object layout in Storage and filters ANTAQ `YYYYCarga.txt` files down to the rows and columns used by the codebase before upload.

Materialize the observed ANTAQ voyages JSON into flat tables:

```powershell
.\venv\Scripts\python.exe .\scripts\materialize_antaq_voyage_tables.py `
  --input-json .\data\processed\cabotage_data\antaq_cabotage_observed_voyages.json `
  --output-dir .\data\processed\cabotage_data\tabular
```

This writes `antaq_voyages.csv`, `antaq_voyage_stops.csv`, and `antaq_voyage_stop_calls.csv`, and can optionally upsert the same rows into Supabase Postgres after the corresponding migration is applied.

Enrich the repository sea matrix with directional MRV fuel-per-transport-work averages derived from observed ANTAQ voyage legs:

```powershell
.\venv\Scripts\python.exe .\scripts\enrich_sea_matrix_with_voyage_efficiency.py `
  --sea-matrix-json .\data\sea_matrix.json `
  --output-json .\data\sea_matrix.json
```

The enricher preserves the existing `matrix` block and appends directional KPI stats under a new top-level section. When the ANTAQ tabular CSVs or MRV lookup JSON are missing locally, it can resolve them from the configured Supabase Storage data bucket.
By default it also prunes the `matrix` down to port pairs observed in ANTAQ with at least one usable MRV KPI match; pass `--keep-unmatched-pairs` to keep ANTAQ-observed pairs without MRV coverage, or `--keep-all-matrix-pairs` to retain the full original matrix.

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
