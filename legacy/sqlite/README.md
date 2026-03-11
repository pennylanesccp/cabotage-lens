# Legacy SQLite Tools

These scripts are kept only for one-off legacy SQLite maintenance and migration work.

- `migrate_sqlite_to_supabase.py`: migrates historical SQLite route and analytics tables into Supabase Postgres.
- `normalize_sqlite_place_names.py`: normalizes historical SQLite place names and removes duplicate rows created by accent variants.

Examples:

```powershell
.\venv\Scripts\python.exe .\legacy\sqlite\migrate_sqlite_to_supabase.py --dry-run --log-level INFO
.\venv\Scripts\python.exe .\legacy\sqlite\normalize_sqlite_place_names.py --dry-run
```

These tools are not part of the shipped app runtime.
