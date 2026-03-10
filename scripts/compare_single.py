#!/usr/bin/env python3
# scripts/compare_single.py
# -*- coding: utf-8 -*-

"""
Single route comparator (CLI).

Compares direct road versus multimodal (cabotage) for one O-D pair.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.database_manager import DEFAULT_DB_PATH, connection_target_summary, db_session, upsert_multimodal_result
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.container_efficiency import CONTAINER_VESSEL_CLASSES, DEFAULT_VESSEL_CLASS
from modules.multimodal.persistence import flatten_evaluation_for_db
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

_log = get_logger("compare_single")


def _print_summary(geo: Dict[str, Any], results: Dict[str, Any]) -> None:
    road = results["road_only"]
    mm = results["multimodal"]
    sea = mm.get("sea", {})
    cmp_data = results["comparison"]

    print("\n" + "-" * 56)
    print(f"ORIGIN:  {geo['origin']['label']}")
    print(f"DESTINY: {geo['destiny']['label']}")
    print("-" * 56)
    print(f"ROAD ONLY ({road['distance_km']:.1f} km)")
    print(f"  Cost: R$ {road['cost']:,.2f}")
    print(f"  CO2e: {road['co2e']:.1f} kg")
    print("-" * 24)
    print(f"MULTIMODAL ({geo['sea_leg']['distance_km']:.1f} km sea)")
    print(f"  Cost: R$ {mm['total_cost']:,.2f}")
    print(f"  CO2e: {mm['total_co2e']:.1f} kg")
    print("-" * 56)

    vessel = results.get("inputs", {}).get("vessel_class")
    fuel_nm = results.get("inputs", {}).get("sea_fuel_per_nm_kg")
    if vessel and fuel_nm:
        print(f"SEA VESSEL CLASS: {vessel} ({float(fuel_nm):.2f} kg/nm)")

    alloc_share = float(sea.get("cargo_allocation_share") or results.get("inputs", {}).get("cargo_allocation_share") or 0.0)
    fuel_twork = results.get("inputs", {}).get("sea_fuel_g_per_tnm")
    mode = sea.get("sailing_fuel_calc_mode") or results.get("inputs", {}).get("sailing_fuel_calc_mode")
    alloc_mode = results.get("inputs", {}).get("allocation_mode_used")
    old_dwt = results.get("inputs", {}).get("share_old_dwt")
    new_teu = results.get("inputs", {}).get("share_new_teu")
    ratio = results.get("inputs", {}).get("ratio_new_vs_old")
    print(
        "SEA ALLOCATION: "
        f"mode={alloc_mode}, "
        f"share={alloc_share:.4f}, "
        f"old_dwt={(f'{float(old_dwt):.4f}' if isinstance(old_dwt, (int, float)) else 'n/a')}, "
        f"new_teu={(f'{float(new_teu):.4f}' if isinstance(new_teu, (int, float)) else 'n/a')}, "
        f"ratio={(f'{float(ratio):.3f}' if isinstance(ratio, (int, float)) else 'n/a')}, "
        f"fuel_g_per_tnm={(f'{float(fuel_twork):.3f}' if isinstance(fuel_twork, (int, float)) else 'n/a')}, "
        f"mode={mode}"
    )

    print(
        "SEA FUEL BREAKDOWN: "
        f"sailing={float(sea.get('fuel_kg_sailing') or 0.0):,.1f} kg, "
        f"hoteling={float(sea.get('hoteling_fuel_kg') or 0.0):,.1f} kg, "
        f"port_ops={float(sea.get('port_ops_fuel_kg') or 0.0):,.1f} kg"
    )

    if sea.get("port_ops"):
        po = sea["port_ops"]
        print(
            "PORT OPS: "
            f"scenario={po.get('resolved_scenario')} "
            f"moves/call={float(po.get('port_moves_per_call') or 0.0):.1f} "
            f"calls={int(po.get('port_calls') or 0)} "
            f"cargo_teu={int(po.get('cargo_teu_resolved') or 0)}"
        )

    savings_pct = float(cmp_data.get("savings_pct") or 0.0)
    status = "BETTER" if savings_pct > 0 else "WORSE"
    print(f"{status}: {savings_pct:.1f}% (R$ {-1 * float(cmp_data['delta_cost']):,.2f})")
    print("-" * 56 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Single route comparison")
    parser.add_argument("--origin", required=True, help="Origin (city/address/coords)")
    parser.add_argument("--destiny", required=True, help="Destiny (city/address/coords)")
    parser.add_argument("--cargo", type=float, default=27.0, help="Cargo mass in tonnes")

    parser.add_argument("--truck", default="semi_27t", help="Truck spec key")
    parser.add_argument("--profile", default="driving-hgv", help="ORS routing profile")
    parser.add_argument("--overwrite", action="store_true", help="Force fresh routing")
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

    parser.add_argument("--table", default="analysis_results", help="Target persisted results table")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        type=Path,
        help="Legacy SQLite path override. Ignored when the Postgres backend is active.",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level, write_to_file=False)
    _log.info("Database target: %s", connection_target_summary(args.db_path))

    from modules.multimodal import build_path_geometry, evaluate_path

    if not args.json:
        _log.info("Routing: %s -> %s (%.3ft)", args.origin, args.destiny, args.cargo)

    geo = build_path_geometry(
        args.origin,
        args.destiny,
        ors_profile=args.profile,
        overwrite_road=args.overwrite,
        db_path=args.db_path,
    )
    if not geo or geo.get("status") != "ok":
        _log.error("Failed to build route geometry.")
        return 1

    results = evaluate_path(
        geo,
        cargo_t=args.cargo,
        truck_key=args.truck,
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
    if not results:
        _log.error("Failed to evaluate path.")
        return 1

    flat_record = flatten_evaluation_for_db(
        origin_name=geo["origin"]["label"],
        destiny_name=geo["destiny"]["label"],
        res=results,
    )

    try:
        with db_session(args.db_path) as conn:
            upsert_multimodal_result(conn, table_name=args.table, **flat_record)
            if not args.json:
                _log.info("Saved result to table '%s'.", args.table)
    except Exception as exc:
        _log.warning("Result persistence failed; returning computed output only: %s", exc)

    if args.json or args.pretty:
        print(json.dumps(results, indent=2 if args.pretty else None, ensure_ascii=False))
    else:
        _print_summary(geo, results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

