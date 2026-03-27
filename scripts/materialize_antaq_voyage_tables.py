#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.cabotage.antaq_voyage_tables import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_VOYAGES_JSON_PATH,
    load_observed_voyages_payload,
    materialize_voyage_tables,
    upsert_tables_to_db,
    write_tables_to_disk,
)
from modules.infra.db.core import connection_target_summary, db_session
from modules.infra.log_manager import init_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize the observed ANTAQ cabotage voyages JSON into tabular voyage, "
            "stop, and call datasets, with optional upsert into Supabase Postgres."
        )
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=DEFAULT_VOYAGES_JSON_PATH,
        help=f"Observed voyages JSON path. Default: {DEFAULT_VOYAGES_JSON_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for normalized CSV outputs. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--include-raw-jsonl",
        action="store_true",
        help="Also write antaq_voyages_raw.jsonl alongside the CSV tables.",
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Upsert the normalized tables into the configured Supabase Postgres database.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional Postgres DSN override. Defaults to SUPABASE_DB_URL or split secrets.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Root log level. Default: INFO.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    init_logging(level=args.log_level, archive_to_storage=False, force_clean=True)

    source_path, payload = load_observed_voyages_payload(args.input_json)
    tables = materialize_voyage_tables(payload, source_path=source_path)
    outputs = write_tables_to_disk(
        tables,
        output_dir=args.output_dir,
        include_raw_jsonl=bool(args.include_raw_jsonl),
    )

    summary: dict[str, object] = {
        "source_json": str(source_path),
        "output_dir": str(Path(args.output_dir).resolve()),
        "voyages_rows": len(tables.voyages),
        "stops_rows": len(tables.stops),
        "stop_calls_rows": len(tables.stop_calls),
        "raw_rows": len(tables.raw_rows),
        "outputs": outputs,
    }

    if args.load_db:
        with db_session(args.database_url) as conn:
            summary["db_target"] = connection_target_summary(args.database_url)
            summary["db_upsert"] = upsert_tables_to_db(conn, tables)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
