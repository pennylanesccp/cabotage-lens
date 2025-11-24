#!/usr/bin/env python3
# scripts/compare_single.py
# -*- coding: utf-8 -*-

"""
Single Route Comparator (CLI).
==============================

Compares Direct Road vs. Multimodal (Cabotage) for a single O->D pair.

Flow:
  1. Build Geometry (modules.multimodal.builder)
  2. Evaluate Costs/Emissions (modules.multimodal.evaluator)
  3. Save to DB (modules.infra.database_manager)
  4. Output JSON/Text

Usage:
  python scripts/compare_single.py --origin "Santos, SP" --destiny "Manaus, AM" --cargo 30
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ───────────────────── Path Bootstrap ─────────────────────
# Ensure we can import 'modules' from repo root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ───────────────────── Imports ─────────────────────
from modules.infra.log_manager import init_logging, get_logger
from modules.infra.database_manager import (
      db_session
    , upsert_multimodal_result
    , DEFAULT_DB_PATH
)
from modules.multimodal import build_path_geometry, evaluate_path

_log = get_logger("compare_single")


# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────

def _flatten_for_db(
      origin_name: str
    , destiny_name: str
    , res: dict
) -> dict:
    """
    Convert the nested evaluator result into the flat dictionary 
    required by `upsert_multimodal_result`.
    """
    road_only = res.get("road_only", {})
    mm = res.get("multimodal", {})
    
    # Sum up the two road legs of the multimodal path
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    
    mm_road_liters = (first.get("liters") or 0.0) + (last.get("liters") or 0.0)
    mm_road_kg = (first.get("fuel_kg") or 0.0) + (last.get("fuel_kg") or 0.0)
    mm_road_cost = (first.get("cost") or 0.0) + (last.get("cost") or 0.0)
    mm_road_co2e = (first.get("co2e") or 0.0) + (last.get("co2e") or 0.0)

    mm_sea = mm.get("sea", {})
    comp = res.get("comparison", {})

    return {
        "origin_name": origin_name,
        "destiny_name": destiny_name,
        "cargo_t": res["inputs"]["cargo_t"],
        
        # Road Baseline
        "road_distance_km": road_only.get("distance_km"),
        "road_fuel_liters": road_only.get("liters"),
        "road_fuel_kg": None, # Evaluator usually returns liters for road; calculate if needed or add to model
        "road_fuel_cost_r": road_only.get("cost"),
        "road_co2e_kg": road_only.get("co2e"),

        # Multimodal Road Parts (First + Last)
        "mm_road_fuel_liters": mm_road_liters,
        "mm_road_fuel_kg": mm_road_kg,
        "mm_road_fuel_cost_r": mm_road_cost,
        "mm_road_co2e_kg": mm_road_co2e,

        # Multimodal Sea Part
        "sea_km": mm_sea.get("distance_km"),
        "sea_fuel_kg": mm_sea.get("fuel_kg"),
        "sea_fuel_cost_r": mm_sea.get("cost"),
        "sea_co2e_kg": mm_sea.get("co2e"),

        # Totals & Deltas
        "total_fuel_kg": None, # Can derive if needed
        "total_fuel_cost_r": mm.get("total_cost"),
        "total_co2e_kg": mm.get("total_co2e"),
        "delta_cost_r": comp.get("delta_cost"),
        "delta_co2e_kg": comp.get("delta_co2e")
    }


# ────────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Single Route Comparison")
    
    # Inputs
    parser.add_argument("--origin", required=True, help="Origin (City/Address/Coords)")
    parser.add_argument("--destiny", required=True, help="Destiny (City/Address/Coords)")
    parser.add_argument("--cargo", type=float, default=27.0, help="Cargo mass (tonnes)")
    
    # Configs
    parser.add_argument("--truck", default="semi_27t", help="Truck spec key")
    parser.add_argument("--profile", default="driving-hgv", help="ORS routing profile")
    parser.add_argument("--overwrite", action="store_true", help="Force fresh routing (ignore cache)")
    
    # Output/DB
    parser.add_argument("--table", default="analysis_results", help="Target SQLite table name")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, type=Path)
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    # 1. Init Logging
    # If outputting JSON, keep logs quiet (stderr only)
    init_logging(level=args.log_level, write_to_file=False)

    # 2. Build Geometry
    if not args.json: 
        _log.info(f"Routing: {args.origin} -> {args.destiny} ({args.cargo}t)")
        
    geo = build_path_geometry(
        args.origin, 
        args.destiny, 
        ors_profile=args.profile, 
        overwrite_road=args.overwrite,
        db_path=args.db_path
    )

    if not geo or geo["status"] != "ok":
        _log.error("Failed to build route geometry.")
        return 1

    # 3. Evaluate Physics/Costs
    results = evaluate_path(geo, cargo_t=args.cargo, truck_key=args.truck)
    if not results:
        _log.error("Failed to evaluate path.")
        return 1

    # 4. Persist to DB
    flat_record = _flatten_for_db(
        origin_name=geo["origin"]["label"],
        destiny_name=geo["destiny"]["label"],
        res=results
    )
    
    with db_session(args.db_path) as conn:
        upsert_multimodal_result(conn, table_name=args.table, **flat_record)
        if not args.json:
            _log.info(f"Saved result to table '{args.table}'")

    # 5. Output
    if args.json or args.pretty:
        print(json.dumps(results, indent=2 if args.pretty else None, ensure_ascii=False))
    else:
        # Human-readable summary
        rd = results["road_only"]
        mm = results["multimodal"]
        cp = results["comparison"]
        
        print("\n" + "─"*50)
        print(f"ORIGIN:  {geo['origin']['label']}")
        print(f"DESTINY: {geo['destiny']['label']}")
        print("─"*50)
        print(f"ROAD ONLY ({rd['distance_km']:.1f} km)")
        print(f"  Cost: R$ {rd['cost']:,.2f}")
        print(f"  CO2e: {rd['co2e']:.1f} kg")
        print("-" * 20)
        print(f"MULTIMODAL ({geo['sea_leg']['distance_km']:.1f} km Sea)")
        print(f"  Cost: R$ {mm['total_cost']:,.2f}")
        print(f"  CO2e: {mm['total_co2e']:.1f} kg")
        print("─"*50)
        
        # Colorized Delta
        savings = cp['savings_pct']
        emoji = "✅" if savings > 0 else "❌"
        print(f"{emoji} SAVINGS: {savings:.1f}%  (R$ {cp['delta_cost']*-1:,.2f})")
        print("─"*50 + "\n")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())