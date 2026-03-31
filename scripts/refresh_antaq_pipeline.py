#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.cabotage.antaq_refresh import (
    DEFAULT_BUCKET,
    DEFAULT_DOWNLOAD_PAGE_URL,
    DEFAULT_MRV_JSON_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    DEFAULT_SEA_MATRIX_PATH,
    DEFAULT_TXT_BASE_URL,
    DEFAULT_VOYAGES_JSON_PATH,
    refresh_antaq_pipeline,
)
from modules.infra.log_manager import init_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download ANTAQ TXT tables for one or more years, rebuild the observed cabotage "
            "voyage artifacts, materialize the tabular outputs, enrich data/sea_matrix.json, "
            "and optionally load Postgres plus sync Supabase Storage."
        )
    )
    parser.add_argument(
        "--years",
        nargs="+",
        required=True,
        help="ANTAQ years to download and rebuild, for example: --years 2024 2025 2026",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=f"Directory for ANTAQ raw TXT files. Default: {DEFAULT_RAW_DIR}",
    )
    parser.add_argument(
        "--voyages-output-json",
        type=Path,
        default=DEFAULT_VOYAGES_JSON_PATH,
        help=f"Observed voyages JSON path. Default: {DEFAULT_VOYAGES_JSON_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for normalized voyage CSV outputs. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--sea-matrix-json",
        type=Path,
        default=DEFAULT_SEA_MATRIX_PATH,
        help=f"Sea matrix JSON to enrich in place. Default: {DEFAULT_SEA_MATRIX_PATH}",
    )
    parser.add_argument(
        "--mrv-json",
        type=Path,
        default=DEFAULT_MRV_JSON_PATH,
        help=f"MRV IMO efficiency JSON path. Default: {DEFAULT_MRV_JSON_PATH}",
    )
    parser.add_argument(
        "--download-page-url",
        default=DEFAULT_DOWNLOAD_PAGE_URL,
        help=f"ANTAQ download page URL. Default: {DEFAULT_DOWNLOAD_PAGE_URL}",
    )
    parser.add_argument(
        "--txt-base-url",
        default=DEFAULT_TXT_BASE_URL,
        help=f"Base URL for ANTAQ TXT/ZIP assets. Default: {DEFAULT_TXT_BASE_URL}",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download raw TXT files even when the target TXT already exists locally.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the ANTAQ portal download step and reuse the raw TXT files already present in data/raw/cabotage_data.",
    )
    parser.add_argument(
        "--include-raw-jsonl",
        action="store_true",
        help="Also emit antaq_voyages_raw.jsonl during materialization.",
    )
    parser.add_argument(
        "--max-gap-hours",
        type=float,
        default=240.0,
        help="Maximum gap between stops used by the observed voyage builder. Default: 240.",
    )
    parser.add_argument(
        "--ensure-db-schema",
        action="store_true",
        help="Apply the ANTAQ voyage table migration before loading Postgres.",
    )
    parser.add_argument(
        "--load-db",
        action="store_true",
        help="Upsert the normalized ANTAQ voyage tables into Supabase Postgres.",
    )
    parser.add_argument(
        "--sync-bucket",
        action="store_true",
        help="Upload the repository data/ tree to Supabase Storage after regeneration.",
    )
    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help=f"Supabase Storage data bucket. Default: {DEFAULT_BUCKET}",
    )
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=50.0,
        help="Per-object Storage size ceiling before gzip compression. Default: 50 MB.",
    )
    parser.add_argument(
        "--keep-all-matrix-pairs",
        action="store_true",
        help="Keep the full base sea matrix instead of pruning to ANTAQ-observed combinations.",
    )
    parser.add_argument(
        "--keep-unmatched-pairs",
        action="store_true",
        help="Keep ANTAQ-observed maritime pairs even when there is no usable MRV KPI match.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds for ANTAQ downloads. Default: 120.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the resulting summary JSON.",
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

    try:
        summary = refresh_antaq_pipeline(
            years=args.years,
            raw_dir=args.raw_dir,
            voyages_output_path=args.voyages_output_json,
            output_dir=args.output_dir,
            sea_matrix_path=args.sea_matrix_json,
            mrv_json_path=args.mrv_json,
            include_raw_jsonl=bool(args.include_raw_jsonl),
            max_gap_hours=float(args.max_gap_hours),
            ensure_db_schema=bool(args.ensure_db_schema),
            load_db=bool(args.load_db),
            sync_bucket=bool(args.sync_bucket),
            bucket=str(args.bucket),
            max_file_mb=float(args.max_file_mb),
            download_page_url=str(args.download_page_url),
            txt_base_url=str(args.txt_base_url),
            force_download=bool(args.force_download),
            skip_download=bool(args.skip_download),
            keep_all_matrix_pairs=bool(args.keep_all_matrix_pairs),
            keep_unmatched_pairs=bool(args.keep_unmatched_pairs),
            timeout_s=float(args.timeout_s),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
