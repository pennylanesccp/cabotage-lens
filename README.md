# CabotageLens: A Multimodal Cost and Carbon Footprint Assessment Tool for Brazilian Freight Transport

CabotageLens is a multimodal freight comparison toolkit for Brazil, focused on road-only versus cabotage-assisted scenarios.

Public repository: `https://github.com/pennylanesccp/cabotage-lens`

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
- `docs/references/` local-only reference papers and workbooks, ignored by Git
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
SUPABASE_STORAGE_LOGS_BUCKET = "cabotage-lens-logs"
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

## Local reference papers

Reference PDFs and private benchmark workbooks are intentionally not tracked in Git. Keep them under `docs/references/` in local clones only. The tracked files `docs/references.bib` and `docs/references_renames.md` preserve the citation and filename map without publishing the papers.

To restore a local research workstation, copy the private reference bundle back to `docs/references/` from a private backup or institution-approved source. Do not stage those files. The repository `.gitignore` ignores `docs/references/` and `*.pdf`, so `git status --short --untracked-files=all` should not list restored papers.

## Install

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run CabotageLens

```powershell
.\run_streamlit.ps1
```

The app reads `.streamlit/secrets.toml` for local runs, shows the Router and Heatmap pages after the access gate succeeds, connects to Supabase Postgres, and keeps runtime logs on stdout/stderr. In Streamlit Community Cloud, set the same values through the app Secrets settings. If `LOG_ARCHIVE_ENABLED=true` and Storage credentials are configured, it also archives compressed JSONL logs to Supabase Storage.

When `SUPABASE_STORAGE_DATA_BUCKET` is configured, runtime loaders prefer the bucket copy of processed cabotage artifacts and cache them locally under `.cache/supabase_data/`.

Every Router calculation and Heatmap run attempts to refresh the ANP Diesel S10 table and the Ship & Bunker Santos VLSFO price before evaluation. Refreshed inputs are kept under `.cache/runtime_fuel_prices/`. If either external source is unavailable or cannot be parsed, the run continues with the last valid persisted input and records the fallback in the live logs. A Heatmap run recalculates all destinations when the refreshed fuel values differ, preventing mixed-price surfaces.

Port operations are always included in Router and Heatmap calculations. The Router displays this setting as a locked control so restored browser/session state cannot silently remove the port-operation boundary.

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

The uploader preserves the `data/...` object layout in Storage and filters ANTAQ `YYYYCarga.txt` files down to the rows and columns used by the codebase before upload. Before synchronizing the canonical `data/sea_matrix.json`, it rejects empty artifacts and verifies that Santos–Manaus has a usable ANTAQ+MRV directional route with resolved intensity coverage and explicit IMO/fallback provenance.

Materialize the observed ANTAQ voyages JSON into flat tables:

```powershell
.\venv\Scripts\python.exe .\scripts\materialize_antaq_voyage_tables.py `
  --input-json .\data\processed\cabotage_data\antaq_cabotage_observed_voyages.json `
  --output-dir .\data\processed\cabotage_data\tabular
```

This writes `antaq_voyages.csv`, `antaq_voyage_stops.csv`, and `antaq_voyage_stop_calls.csv`, and can optionally upsert the same rows into Supabase Postgres after the corresponding migration is applied.

Enrich the repository sea matrix with directional MRV fuel-per-transport-work averages derived from complete observed ANTAQ voyage corridors:

```powershell
.\venv\Scripts\python.exe .\scripts\enrich_sea_matrix_with_voyage_efficiency.py `
  --sea-matrix-json .\data\sea_matrix.json `
  --output-json .\data\sea_matrix.json
```

For every voyage, the enricher evaluates every ordered origin-destination port pair, including direct voyages and complete multi-stop corridors. A voyage contributes once to a given ordered pair; when repeated port calls create more than one eligible slice, the same current rule is applied within that voyage (direct first, otherwise shortest distance). Fuel is summed over the observed sublegs using the reconstructed cargo aboard, subleg distance, and voyage intensity. Corridors are never assembled from legs belonging to different voyages. Across voyages, the current selection rule remains explicit: prefer an observed direct corridor; otherwise select the shortest complete observed corridor.

Known ANTAQ terminal names are resolved to their canonical port complex. Consecutive calls that resolve to the same canonical port are collapsed only after all cargo movements have been retained and summed. Distinct port pairs use a positive sea-matrix distance first; if that value is absent or nonpositive, the enricher uses the tracked port coordinates as an explicit `haversine_fallback` and reports that source in the corridor indicators.

The voyage-stop input is the normalized containerized-cargo call sequence produced by the ANTAQ pipeline; it should not be read as an inventory of physical calls with no observed container movement. When a resolved voyage or subleg has zero observed transport work, observed fuel remains zero while the resolved vessel intensities are retained through an explicitly labeled arithmetic mean so scenario cargo can still be evaluated without a `0/0` gap.

Intensity resolution is recorded per voyage. The hierarchy is an exact latest positive EU MRV match by IMO, then an available robust vessel-class statistic, then a robust ship-type statistic (the container-ship type is the documented default for the containerized ANTAQ scope). Class fallbacks use the tracked `trimmed_mean_1pct` and fall back to the class median only when that field is unavailable. Ship-type fallbacks symmetrically remove the lowest and highest 1% of latest positive IMO values (integer floor per tail) before taking the mean; samples too small to remove at least one observation per tail use the median. Exact IMO values are never trimmed. Provenance records the statistic, rule, raw/retained sample sizes, excluded count, bounds, and untrimmed summaries. Aggregate indicators keep exact IMO matches separate from class/type fallbacks.

The enricher preserves the existing `matrix` block and appends selected-corridor statistics, evaluated corridor alternatives, subleg calculations, and intensity provenance under the directional section. An explicitly available local matrix is always used as the base, preventing an invalid remote cache from overwriting it. When the ANTAQ tabular CSVs or MRV lookup JSON are missing locally, it can resolve them from the configured Supabase Storage data bucket. By default it prunes the distance matrix to observed usable combinations; pass `--keep-unmatched-pairs` to retain observed pairs with unresolved intensity, or `--keep-all-matrix-pairs` to retain the full original distance matrix.

## Logging

- Console output is always enabled.
- `LOG_LEVEL` controls the initial Streamlit verbosity and can still be changed in the app sidebar.
- With `LOG_LEVEL = "DEBUG"`, single-route evaluations emit structured `single_eval` lines for each routing and calculation stage, including cache/provider or tracked-asset provenance. Bulk evaluation tracing is unchanged.
- `LOG_ARCHIVE_ENABLED=true` enables Supabase Storage archival.
- Archived log entries include timestamp, level, module, message, and any bound run or scenario identifiers.

## Migrations

Apply these SQL files to Supabase:

- `supabase/migrations/20260309_000001_carbon_footprint_core.sql`
- `supabase/migrations/20260310_000002_bulk_heatmap_runs.sql`
- `supabase/migrations/20260312_000003_bulk_pipeline_perf.sql`
- `supabase/migrations/20260313_000004_normalized_location_route_bulk_schema.sql`
- `supabase/migrations/20260324_000005_bulk_failure_diagnostics.sql`
- `supabase/migrations/20260327_000006_antaq_voyage_tables.sql`

## Tests

This repository now uses unit tests that mock the Postgres and Storage boundaries instead of relying on local file-database fixtures.

## Notes

- The route cache is durable and shared through Postgres.
- The heatmap page reads and writes only the Supabase-backed bulk tables.
- Bulk heatmap runs persist newly geocoded location aliases in batches, so an interrupted large run can reuse completed geocoding work on its next attempt.
- PostgreSQL advisory locks prevent concurrent workers from processing the same origin, scenario, and destination set.
- There is no local database fallback.
