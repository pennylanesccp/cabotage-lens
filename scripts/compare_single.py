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

from modules.core.env_loader import load_repo_env

load_repo_env(ROOT / ".env")

from modules.infra.database_manager import DEFAULT_DB_PATH, db_session, upsert_multimodal_result
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.container_efficiency import CONTAINER_VESSEL_CLASSES, DEFAULT_VESSEL_CLASS
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

_log = get_logger("compare_single")
_DIESEL_DENSITY_KG_PER_L = 0.84


def _flatten_for_db(origin_name: str, destiny_name: str, res: Dict[str, Any]) -> Dict[str, Any]:
    """Convert nested evaluator output into flat DB payload."""
    road_only = res.get("road_only", {})
    mm = res.get("multimodal", {})

    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    comp = res.get("comparison", {})

    road_liters = float(road_only.get("liters") or 0.0)
    road_fuel_kg = float(road_only.get("fuel_kg") or (road_liters * _DIESEL_DENSITY_KG_PER_L))

    mm_road_liters = float(first.get("liters") or 0.0) + float(last.get("liters") or 0.0)
    mm_road_kg = float(first.get("fuel_kg") or 0.0) + float(last.get("fuel_kg") or 0.0)
    if mm_road_kg <= 0.0 and mm_road_liters > 0.0:
        mm_road_kg = mm_road_liters * _DIESEL_DENSITY_KG_PER_L

    sea_fuel_kg = float(sea.get("fuel_kg") or 0.0)

    total_fuel_kg = mm_road_kg + sea_fuel_kg

    return {
        "origin_name": origin_name,
        "destiny_name": destiny_name,
        "cargo_t": res["inputs"]["cargo_t"],
        "road_distance_km": road_only.get("distance_km"),
        "road_fuel_liters": road_liters,
        "road_fuel_kg": road_fuel_kg,
        "road_fuel_cost_r": road_only.get("cost"),
        "road_co2e_kg": road_only.get("co2e"),
        "mm_road_fuel_liters": mm_road_liters,
        "mm_road_fuel_kg": mm_road_kg,
        "mm_road_fuel_cost_r": float(first.get("cost") or 0.0) + float(last.get("cost") or 0.0),
        "mm_road_co2e_kg": float(first.get("co2e") or 0.0) + float(last.get("co2e") or 0.0),
        "sea_km": sea.get("distance_km"),
        "sea_fuel_kg": sea_fuel_kg,
        "sea_fuel_cost_r": sea.get("cost"),
        "sea_co2e_kg": sea.get("co2e"),
        "total_fuel_kg": total_fuel_kg,
        "total_fuel_cost_r": mm.get("total_cost"),
        "total_co2e_kg": mm.get("total_co2e"),
        "delta_cost_r": comp.get("delta_cost"),
        "delta_co2e_kg": comp.get("delta_co2e"),
    }


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
            f"calls={int(po.get('port_calls') or 0)}"
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
        "--include-port-ops",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include port operations (RTG/terminal truck/STS placeholder)",
    )
    parser.add_argument(
        "--port-moves-per-call",
        type=float,
        default=None,
        help="Quay-side container moves per port call (defaults to scenario median when omitted)",
    )
    parser.add_argument(
        "--port-ops-scenario",
        default=DEFAULT_PORT_OPS_SCENARIO,
        choices=list_port_ops_scenarios(),
        help="Port ops scenario from data/processed/cabotage_data/port_ops_params_santos.json",
    )

    parser.add_argument("--table", default="analysis_results", help="Target SQLite table")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, type=Path)
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level, write_to_file=False)

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
        port_ops_scenario=str(args.port_ops_scenario),
    )
    if not results:
        _log.error("Failed to evaluate path.")
        return 1

    flat_record = _flatten_for_db(
        origin_name=geo["origin"]["label"],
        destiny_name=geo["destiny"]["label"],
        res=results,
    )

    with db_session(args.db_path) as conn:
        upsert_multimodal_result(conn, table_name=args.table, **flat_record)
        if not args.json:
            _log.info("Saved result to table '%s'.", args.table)

    if args.json or args.pretty:
        print(json.dumps(results, indent=2 if args.pretty else None, ensure_ascii=False))
    else:
        _print_summary(geo, results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

