#!/usr/bin/env python3
# scripts/run_validation_batch_001b.py
# -*- coding: utf-8 -*-

"""Run or stage Batch 001B validation output artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger, init_logging
from modules.validation.batch_001b import (
    ValidationConfigError,
    build_rows,
    default_output_csv_path,
    default_output_json_path,
    load_validation_config,
    write_output_csv,
    write_output_json,
)

_log = get_logger("run_validation_batch_001b")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create Batch 001B validation output artifacts from explicit config."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("docs/validation/tf_validation_batch_001b_config_template.json"),
        help="Batch 001B JSON config file.",
    )
    parser.add_argument("--output-csv", type=Path, default=None, help="CSV output path.")
    parser.add_argument("--output-json", type=Path, default=None, help="JSON output path.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run model_rerun cases. Without this, model cases are emitted as planned rows only.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Write only JSON output.",
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Write only CSV output.",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    init_logging(level=args.log_level)

    if args.json_only and args.csv_only:
        parser.error("--json-only and --csv-only are mutually exclusive")

    try:
        config = load_validation_config(args.config)
        rows = build_rows(config, execute=bool(args.execute))
        csv_path = args.output_csv or default_output_csv_path(config)
        json_path = args.output_json or default_output_json_path(config)
        if not args.json_only:
            write_output_csv(rows, csv_path)
            _log.info("Batch 001B CSV written to %s", csv_path)
        if not args.csv_only:
            write_output_json(rows, json_path)
            _log.info("Batch 001B JSON written to %s", json_path)
    except ValidationConfigError as exc:
        _log.error(str(exc))
        return 2
    except Exception as exc:
        _log.exception("Batch 001B validation export failed: %s", exc)
        return 1

    _log.info(
        "Batch 001B validation export complete: rows=%d execute=%s",
        len(rows),
        bool(args.execute),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
