#!/usr/bin/env python3
# scripts/compare_bulk.py
# -*- coding: utf-8 -*-

"""
Bulk comparison CLI.

Processes multiple destinations for one fixed origin and stores bulk analytical
outputs in the configured database backend plus a summary CSV.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.database_manager import DEFAULT_BULK_RESULTS_TABLE, connection_target_summary
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.bulk import load_destinations
from modules.multimodal.container_efficiency import CONTAINER_VESSEL_CLASSES, DEFAULT_VESSEL_CLASS
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios
from modules.multimodal import run_bulk_evaluation

_log = get_logger("compare_bulk")


def _write_summary_csv(rows: List[Dict[str, object]], output_csv: Path) -> None:
    if not rows:
        return

    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk route comparison")
    parser.add_argument("--origin", required=True, help="Fixed origin")
    parser.add_argument("--dests-file", required=True, type=Path, help="Path to destinations .txt")
    parser.add_argument(
        "--destination-set-id",
        default=None,
        help="Stable identifier for the destination universe; defaults to the destinations filename.",
    )

    parser.add_argument("--cargo", type=float, default=27.0, help="Cargo mass in tonnes")
    parser.add_argument("--truck", default="semi_27t", help="Truck profile")
    parser.add_argument("--profile", default="driving-hgv", help="Routing profile")
    parser.add_argument("--overwrite", action="store_true", help="Force rerouting of road-distance cache")
    parser.add_argument(
        "--shuffle-destinations",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Shuffle deduplicated destinations before the exact-routing pass",
    )
    parser.add_argument(
        "--shuffle-seed",
        type=int,
        default=None,
        help="Optional deterministic seed for destination shuffling",
    )
    parser.add_argument(
        "--approximation-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Approximate direct-road distance in bulk results when exact road routing is unavailable",
    )
    parser.add_argument(
        "--disable-approximation-fallback",
        dest="approximation_fallback",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--geocode-workers",
        type=int,
        default=4,
        help="Maximum concurrent destination geocoding workers",
    )
    parser.add_argument(
        "--route-workers",
        type=int,
        default=8,
        help="Maximum concurrent geometry/routing workers",
    )
    parser.add_argument(
        "--persist-batch-size",
        type=int,
        default=64,
        help="Bulk result rows to buffer before flushing batched DB writes",
    )
    parser.add_argument(
        "--vessel-class",
        default=DEFAULT_VESSEL_CLASS,
        choices=list(CONTAINER_VESSEL_CLASSES),
        help="Container vessel class from data/processed/cabotage_data MRV artifact",
    )
    parser.add_argument(
        "--include-hoteling",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include at-berth hoteling fuel/emissions",
    )
    parser.add_argument(
        "--hoteling-hours-per-call",
        type=float,
        default=14.0,
        help="Hoteling hours per port call",
    )
    parser.add_argument(
        "--port-calls",
        type=int,
        default=2,
        help="Port calls per voyage",
    )
    parser.add_argument(
        "--cargo-teu",
        type=float,
        default=None,
        help="Optional cargo amount in TEU (if omitted, derived from cargo_t / t_per_teu_default)",
    )
    parser.add_argument(
        "--t-per-teu-default",
        type=float,
        default=14.0,
        help="Default tonnes per TEU used when cargo_teu is omitted",
    )
    parser.add_argument(
        "--allocation-mode",
        choices=["auto", "teu_share", "dwt_share"],
        default="auto",
        help="Cargo allocation mode for maritime fuel attribution",
    )
    parser.add_argument(
        "--allocation-load-factor",
        type=float,
        default=0.8,
        help="Operational TEU load factor for teu_share mode (default from Costa papers: 0.8)",
    )
    parser.add_argument(
        "--full-call-mode",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use scenario terminal-call moves distribution instead of cargo-based TEU scaling",
    )
    parser.add_argument(
        "--include-port-ops",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include port operations (RTG/terminal truck/STS placeholder)",
    )
    parser.add_argument(
        "--port-moves-per-call",
        type=float,
        default=None,
        help="Quay-side container moves per port call (defaults to cargo TEU unless --full-call-mode)",
    )
    parser.add_argument(
        "--port-ops-scenario",
        default=DEFAULT_PORT_OPS_SCENARIO,
        choices=list_port_ops_scenarios(),
        help="Port ops scenario from data/processed/cabotage_data/port_ops_params_santos.json",
    )
    parser.add_argument("--output-csv", default="bulk_results_summary.csv", type=Path)
    parser.add_argument("--results-table", default=DEFAULT_BULK_RESULTS_TABLE, help="Target bulk results table")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level)
    _log.info("Database target: %s", connection_target_summary())

    try:
        destinations = load_destinations(args.dests_file)
    except Exception as exc:
        _log.critical(str(exc))
        return 1

    if not destinations:
        _log.warning("Destinations file is empty.")
        return 0

    outcome = run_bulk_evaluation(
        origin=args.origin,
        dest_list=destinations,
        cargo_t=args.cargo,
        truck_key=args.truck,
        profile=args.profile,
        overwrite_road=args.overwrite,
        results_table=args.results_table,
        vessel_class=args.vessel_class,
        include_hoteling=bool(args.include_hoteling),
        hoteling_hours_per_call=float(args.hoteling_hours_per_call),
        port_calls=int(args.port_calls),
        include_port_ops=bool(args.include_port_ops),
        port_moves_per_call=args.port_moves_per_call,
        cargo_teu=args.cargo_teu,
        t_per_teu_default=float(args.t_per_teu_default),
        allocation_mode=(None if str(args.allocation_mode).lower() == "auto" else str(args.allocation_mode).lower()),
        allocation_load_factor=float(args.allocation_load_factor),
        full_call_mode=bool(args.full_call_mode),
        port_ops_scenario=str(args.port_ops_scenario),
        destination_set_id=str(args.destination_set_id or args.dests_file.name),
        shuffle_destinations=bool(args.shuffle_destinations),
        shuffle_seed=args.shuffle_seed,
        approximation_fallback=bool(args.approximation_fallback),
        max_geocode_workers=max(int(args.geocode_workers), 1),
        max_route_workers=max(int(args.route_workers), 1),
        persist_batch_size=max(int(args.persist_batch_size), 1),
    )

    _write_summary_csv(outcome["summary_rows"], args.output_csv)
    _log.info("Summary CSV written to: %s", args.output_csv)
    _log.info(
        (
            "Bulk CLI finished. success=%d fail=%d exact_success=%d approximated_success=%d "
            "unresolved_failures=%d duration_s=%.2f run_id=%s shuffle_seed=%s"
        ),
        int(outcome["success_count"]),
        int(outcome["fail_count"]),
        int(outcome.get("exact_success_count") or 0),
        int(outcome.get("approximated_success_count") or 0),
        int(outcome.get("unresolved_fail_count") or 0),
        float(outcome["duration_s"]),
        outcome.get("run_id"),
        outcome.get("shuffle_seed_used"),
    )
    perf = outcome.get("performance") or {}
    timings = perf.get("timings_s") or {}
    counts = perf.get("counts") or {}
    _log.info(
        (
            "Bulk performance: bootstrap=%.2fs geocode=%.2fs geometry=%.2fs exact=%.2fs approx=%.2fs "
            "db_read=%.2fs db_write=%.2fs direct_hit=%.0f direct_miss=%.0f last_hit=%.0f last_miss=%.0f"
        ),
        float(timings.get("bootstrap_s") or 0.0),
        float(timings.get("destination_geocode_s") or 0.0),
        float(timings.get("geometry_acquisition_s") or 0.0),
        float(timings.get("exact_pass_s") or 0.0),
        float(timings.get("approximation_pass_s") or 0.0),
        float(timings.get("db_read_s") or 0.0),
        float(timings.get("db_write_s") or 0.0),
        float(counts.get("road_direct_cache_hits") or 0.0),
        float(counts.get("road_direct_cache_misses") or 0.0),
        float(counts.get("last_mile_cache_hits") or 0.0),
        float(counts.get("last_mile_cache_misses") or 0.0),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
