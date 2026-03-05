#!/usr/bin/env python3
# scripts/compare_bulk.py
# -*- coding: utf-8 -*-

"""
Bulk comparison CLI.

Processes multiple destinations for one fixed origin and stores multimodal
comparison outputs in SQLite plus a summary CSV.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.core.env_loader import load_repo_env

load_repo_env(ROOT / ".env")

from modules.infra.database_manager import DEFAULT_DB_PATH, db_session, upsert_multimodal_result
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.container_efficiency import CONTAINER_VESSEL_CLASSES, DEFAULT_VESSEL_CLASS
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios
from scripts.compare_single import _flatten_for_db

_log = get_logger("compare_bulk")


def _load_destinations(path: Path) -> List[str]:
    """Read clean non-empty lines from file."""
    if not path.exists():
        raise FileNotFoundError(f"Destinations file not found: {path}")

    out: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip().lstrip("\ufeff")
            if text and not text.startswith("#"):
                out.append(text)
    return out


def _write_summary_csv(rows: List[Dict[str, object]], output_csv: Path) -> None:
    if not rows:
        return

    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def run_bulk(
    origin: str,
    dest_list: List[str],
    cargo_t: float,
    truck_key: str,
    profile: str,
    overwrite: bool,
    db_path: Path,
    output_csv: Path,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: float | None,
    cargo_teu: float | None,
    t_per_teu_default: float,
    allocation_mode: str | None,
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
) -> None:
    """Process all destinations sequentially."""
    from modules.multimodal import build_path_geometry, evaluate_path
    success_count = 0
    fail_count = 0
    t0_global = time.time()
    summary_rows: List[Dict[str, object]] = []

    _log.info("Starting batch: origin=%r count=%d", origin, len(dest_list))

    for i, dest in enumerate(dest_list, start=1):
        t0 = time.time()
        _log.info("[%d/%d] Processing %s", i, len(dest_list), dest)

        try:
            geo = build_path_geometry(
                origin,
                dest,
                ors_profile=profile,
                overwrite_road=overwrite,
                db_path=db_path,
            )
            if not geo or geo.get("status") != "ok":
                raise RuntimeError("Geometry build failed")

            res = evaluate_path(
                geo,
                cargo_t=cargo_t,
                truck_key=truck_key,
                vessel_class=vessel_class,
                include_hoteling=include_hoteling,
                hoteling_hours_per_call=hoteling_hours_per_call,
                port_calls=port_calls,
                include_port_ops=include_port_ops,
                port_moves_per_call=port_moves_per_call,
                cargo_teu=cargo_teu,
                t_per_teu_default=t_per_teu_default,
                allocation_mode=allocation_mode,
                allocation_load_factor=allocation_load_factor,
                full_call_mode=full_call_mode,
                port_ops_scenario=port_ops_scenario,
            )
            if not res:
                raise RuntimeError("Path evaluation failed")

            flat = _flatten_for_db(geo["origin"]["label"], geo["destiny"]["label"], res)
            with db_session(db_path) as conn:
                upsert_multimodal_result(conn, table_name="bulk_results", **flat)

            row: Dict[str, object] = {
                "destiny": dest,
                "status": "ok",
                "vessel_class": res.get("inputs", {}).get("vessel_class"),
                "include_hoteling": res.get("inputs", {}).get("include_hoteling"),
                "hoteling_hours_total": res.get("inputs", {}).get("hoteling_hours_total"),
                "include_port_ops": res.get("inputs", {}).get("include_port_ops"),
                "port_ops_scenario": res.get("inputs", {}).get("port_ops_scenario_resolved"),
                "port_moves_per_call": res.get("inputs", {}).get("port_moves_per_call_resolved"),
                "cargo_teu_resolved": res.get("inputs", {}).get("cargo_teu_resolved"),
                "allocation_mode_used": res.get("inputs", {}).get("allocation_mode_used"),
                "allocation_share": res.get("inputs", {}).get("cargo_allocation_share"),
                "allocation_share_old_dwt": res.get("inputs", {}).get("share_old_dwt"),
                "allocation_share_new_teu": res.get("inputs", {}).get("share_new_teu"),
                "allocation_ratio_new_vs_old": res.get("inputs", {}).get("ratio_new_vs_old"),
                "road_cost": flat.get("road_fuel_cost_r"),
                "mm_cost": flat.get("total_fuel_cost_r"),
                "delta_cost": flat.get("delta_cost_r"),
                "savings_pct": res.get("comparison", {}).get("savings_pct"),
                "road_co2e": flat.get("road_co2e_kg"),
                "mm_co2e": flat.get("total_co2e_kg"),
            }
            summary_rows.append(row)

            dt = time.time() - t0
            _log.info("Done %s in %.2fs. Savings: %.1f%%", dest, dt, float(row["savings_pct"] or 0.0))
            success_count += 1

        except Exception as e:
            _log.error("Failed processing %s: %s", dest, e)
            fail_count += 1
            summary_rows.append({"destiny": dest, "status": "error", "error_msg": str(e)})

    _write_summary_csv(summary_rows, output_csv)
    _log.info("Summary CSV written to: %s", output_csv)

    duration = time.time() - t0_global
    _log.info("Batch complete. success=%d fail=%d time=%.1fs", success_count, fail_count, duration)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk route comparison")
    parser.add_argument("--origin", required=True, help="Fixed origin")
    parser.add_argument("--dests-file", required=True, type=Path, help="Path to destinations .txt")

    parser.add_argument("--cargo", type=float, default=27.0, help="Cargo mass in tonnes")
    parser.add_argument("--truck", default="semi_27t", help="Truck profile")
    parser.add_argument("--profile", default="driving-hgv", help="Routing profile")
    parser.add_argument("--overwrite", action="store_true", help="Force rerouting")
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
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, type=Path)
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level)

    try:
        destinations = _load_destinations(args.dests_file)
    except Exception as e:
        _log.critical(str(e))
        return 1

    if not destinations:
        _log.warning("Destinations file is empty.")
        return 0

    run_bulk(
        origin=args.origin,
        dest_list=destinations,
        cargo_t=args.cargo,
        truck_key=args.truck,
        profile=args.profile,
        overwrite=args.overwrite,
        db_path=args.db_path,
        output_csv=args.output_csv,
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
