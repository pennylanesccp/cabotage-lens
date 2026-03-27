#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.cabotage.sea_matrix_efficiency import (
    DEFAULT_MRV_JSON_PATH,
    DEFAULT_SEA_MATRIX_PATH,
    DEFAULT_STOPS_CSV_PATH,
    DEFAULT_VOYAGES_CSV_PATH,
    enrich_sea_matrix_with_efficiency,
    write_enriched_sea_matrix,
)
from modules.infra.log_manager import init_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich data/sea_matrix.json with directional average fuel-per-transport-work "
            "statistics derived from ANTAQ voyage segments and MRV IMO KPIs."
        )
    )
    parser.add_argument(
        "--sea-matrix-json",
        type=Path,
        default=DEFAULT_SEA_MATRIX_PATH,
        help=f"Base sea matrix JSON. Default: {DEFAULT_SEA_MATRIX_PATH}",
    )
    parser.add_argument(
        "--voyages-csv",
        type=Path,
        default=DEFAULT_VOYAGES_CSV_PATH,
        help=f"Normalized ANTAQ voyages CSV. Default: {DEFAULT_VOYAGES_CSV_PATH}",
    )
    parser.add_argument(
        "--stops-csv",
        type=Path,
        default=DEFAULT_STOPS_CSV_PATH,
        help=f"Normalized ANTAQ voyage stops CSV. Default: {DEFAULT_STOPS_CSV_PATH}",
    )
    parser.add_argument(
        "--mrv-json",
        type=Path,
        default=DEFAULT_MRV_JSON_PATH,
        help=f"MRV efficiency lookup JSON. Default: {DEFAULT_MRV_JSON_PATH}",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_SEA_MATRIX_PATH,
        help=f"Output path for the enriched sea matrix. Default: {DEFAULT_SEA_MATRIX_PATH}",
    )
    parser.add_argument(
        "--keep-all-matrix-pairs",
        action="store_true",
        help="Keep every original matrix pair instead of pruning to observed possible combinations.",
    )
    parser.add_argument(
        "--keep-unmatched-pairs",
        action="store_true",
        help="Keep ANTAQ-observed pairs even when no usable MRV KPI match was found for them.",
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

    payload, summary = enrich_sea_matrix_with_efficiency(
        sea_matrix_path=args.sea_matrix_json,
        voyages_csv_path=args.voyages_csv,
        stops_csv_path=args.stops_csv,
        mrv_json_path=args.mrv_json,
        possible_pairs_only=not bool(args.keep_all_matrix_pairs),
        matched_pairs_only=not bool(args.keep_unmatched_pairs),
    )
    output_path = write_enriched_sea_matrix(payload, output_path=args.output_json)

    result = {
        "output_json": str(output_path),
        **summary,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
