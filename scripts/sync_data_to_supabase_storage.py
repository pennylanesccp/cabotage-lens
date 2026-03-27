#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modules.infra.data_bucket_sync import build_upload_plan, execute_upload_plan
from modules.infra.log_manager import init_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload the repository data/ folder to Supabase Storage, filtering "
            "ANTAQ Carga files down to the rows and columns used by the codebase."
        )
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Local data root to upload. Default: ./data",
    )
    parser.add_argument(
        "--bucket",
        default="cabotage-lens",
        help="Supabase Storage bucket for data assets. Default: cabotage-lens",
    )
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=50.0,
        help="Per-object size ceiling before gzip compression is applied. Default: 50 MB.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the upload plan without sending anything to Supabase Storage.",
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

    plan = build_upload_plan(
        data_root=args.data_root.resolve(),
        max_file_size_bytes=int(args.max_file_mb * 1024 * 1024),
    )
    try:
        summary = execute_upload_plan(
            plan=plan,
            bucket=args.bucket,
            dry_run=bool(args.dry_run),
        )
    except RuntimeError as exc:
        message = str(exc)
        print(f"ERROR: {message}", file=sys.stderr)
        if "data assets are not configured" in message.lower():
            print(
                "Missing secrets for Supabase Storage upload. "
                "Add SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY, "
                "and either SUPABASE_URL or SUPABASE_PROJECT_REF to .streamlit/secrets.toml.",
                file=sys.stderr,
            )
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
