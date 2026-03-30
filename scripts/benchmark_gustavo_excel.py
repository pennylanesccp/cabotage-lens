#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS, CONTAINER_VESSEL_CLASSES
from modules.multimodal.gustavo_benchmark import (
    DEFAULT_BENCHMARK_CSV_PATH,
    DEFAULT_BENCHMARK_JSON_PATH,
    DEFAULT_GUSTAVO_WORKBOOK_PATH,
    compare_gustavo_pairs_with_model,
    load_gustavo_workbook_pairs,
    summarize_gustavo_comparison,
    write_gustavo_benchmark_outputs,
)
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

_log = get_logger("benchmark_gustavo_excel")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Gustavo Costa's workbook pairs against the app model using the 1 TEU / 14 t benchmark."
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_GUSTAVO_WORKBOOK_PATH,
        help="Path to Gustavo's Excel workbook.",
    )
    parser.add_argument(
        "--city-pair",
        action="append",
        default=[],
        help="Optional workbook pair filter in the form 'Origin|Destiny'. Repeat as needed.",
    )
    parser.add_argument("--cargo-t", type=float, default=14.0, help="Benchmark cargo mass in tonnes.")
    parser.add_argument("--cargo-teu", type=float, default=1.0, help="Benchmark cargo volume in TEU.")
    parser.add_argument(
        "--t-per-teu-default",
        type=float,
        default=14.0,
        help="Default tonnes per TEU used by the model.",
    )
    parser.add_argument(
        "--allocation-load-factor",
        type=float,
        default=0.8,
        help="Operational TEU load factor used for allocation.",
    )
    parser.add_argument(
        "--vessel-class",
        default=DEFAULT_VESSEL_CLASS,
        choices=list(CONTAINER_VESSEL_CLASSES),
        help="Fallback vessel class when no directional sea-matrix KPI is available.",
    )
    parser.add_argument(
        "--include-hoteling",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include hoteling in the model run (it will still be skipped automatically when the route KPI already embeds it).",
    )
    parser.add_argument(
        "--hoteling-hours-per-call",
        type=float,
        default=14.0,
        help="Hoteling hours per port call.",
    )
    parser.add_argument("--port-calls", type=int, default=2, help="Port calls per voyage.")
    parser.add_argument(
        "--include-port-ops",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include terminal and port operations in the model run.",
    )
    parser.add_argument(
        "--full-call-mode",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use terminal-level full-call moves instead of cargo-scaled moves.",
    )
    parser.add_argument(
        "--port-ops-scenario",
        default=DEFAULT_PORT_OPS_SCENARIO,
        choices=list_port_ops_scenarios(),
        help="Port ops scenario key.",
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Only parse the workbook and write the benchmark pairs without running the app model.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_BENCHMARK_CSV_PATH,
        help="Destination CSV path for pair-level comparison rows.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_BENCHMARK_JSON_PATH,
        help="Destination JSON path for the summary payload.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the summary JSON.")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    init_logging(level=args.log_level)

    workbook_pairs, workbook_summary = load_gustavo_workbook_pairs(
        workbook_path=args.workbook,
        selected_pairs=args.city_pair,
    )
    if not workbook_pairs:
        _log.error("No comparable workbook pairs were found.")
        return 1

    if args.skip_model:
        comparison_rows = [
            {
                **pair.__dict__,
                "cargo_t": float(args.cargo_t),
                "cargo_teu": float(args.cargo_teu),
                "status": "skipped_model",
                "error": None,
            }
            for pair in workbook_pairs
        ]
    else:
        try:
            comparison_rows = compare_gustavo_pairs_with_model(
                workbook_pairs,
                cargo_t=float(args.cargo_t),
                cargo_teu=float(args.cargo_teu),
                t_per_teu_default=float(args.t_per_teu_default),
                allocation_load_factor=float(args.allocation_load_factor),
                include_hoteling=bool(args.include_hoteling),
                hoteling_hours_per_call=float(args.hoteling_hours_per_call),
                port_calls=int(args.port_calls),
                include_port_ops=bool(args.include_port_ops),
                full_call_mode=bool(args.full_call_mode),
                port_ops_scenario=str(args.port_ops_scenario),
                vessel_class=str(args.vessel_class),
            )
        except Exception as exc:
            _log.error("Failed to run the app model for workbook benchmarking: %s", exc)
            comparison_rows = [
                {
                    **pair.__dict__,
                    "cargo_t": float(args.cargo_t),
                    "cargo_teu": float(args.cargo_teu),
                    "status": "error",
                    "error": str(exc),
                }
                for pair in workbook_pairs
            ]

    summary = summarize_gustavo_comparison(comparison_rows, workbook_summary)
    output_csv, output_json = write_gustavo_benchmark_outputs(
        comparison_rows,
        summary,
        output_csv_path=args.output_csv,
        output_json_path=args.output_json,
    )

    payload = {
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        **summary,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
