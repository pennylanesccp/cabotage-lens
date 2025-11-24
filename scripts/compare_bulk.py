#!/usr/bin/env python3
# scripts/compare_bulk.py
# -*- coding: utf-8 -*-

"""
Bulk Comparison CLI.
====================

Reads a list of destinations from a text file and performs a multimodal
comparison (Road vs. Cabotage) for each one against a fixed Origin.

Features:
  - Efficiently processes hundreds of cities.
  - Skips blank lines or comments (#).
  - Persists results to SQLite automatically.
  - Exports a summary CSV at the end.
  - Resilient: Errors in one city don't crash the whole batch.

Usage:
  python scripts/compare_bulk.py \
      --origin "São Paulo, SP" \
      --dests-file data/processed/destinies/city_dests_over50k.txt \
      --cargo 30
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import List

# ───────────────────── Path Bootstrap ─────────────────────
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
# Re-use the flattening helper from single script logic
from scripts.compare_single import _flatten_for_db

_log = get_logger("compare_bulk")


# ────────────────────────────────────────────────────────────────────────────────
# Logic
# ────────────────────────────────────────────────────────────────────────────────

def _load_destinations(path: Path) -> List[str]:
    """Read clean non-empty lines from file."""
    if not path.exists():
        raise FileNotFoundError(f"Destinations file not found: {path}")
    
    clean_lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                clean_lines.append(s)
    return clean_lines


def run_bulk(
      origin: str
    , dest_list: List[str]
    , cargo_t: float
    , truck_key: str
    , profile: str
    , overwrite: bool
    , db_path: Path
    , output_csv: Path
) -> None:
    """Process all destinations sequentially."""
    
    success_count = 0
    fail_count = 0
    t0_global = time.time()

    # We'll collect summary data for the CSV export
    summary_rows = []

    _log.info(f"Starting batch: Origin='{origin}', Count={len(dest_list)} cities")

    for i, dest in enumerate(dest_list, 1):
        t0 = time.time()
        _log.info(f"[{i}/{len(dest_list)}] Processing: {dest}...")

        try:
            # 1. Build Geometry
            geo = build_path_geometry(
                origin, dest, 
                ors_profile=profile, 
                overwrite_road=overwrite,
                db_path=db_path
            )
            
            if not geo:
                _log.warning(f"Skipped {dest}: Geometry build failed.")
                fail_count += 1
                continue

            # 2. Evaluate
            res = evaluate_path(geo, cargo_t=cargo_t, truck_key=truck_key)
            
            # 3. Save to DB
            flat = _flatten_for_db(geo["origin"]["label"], geo["destiny"]["label"], res)
            
            with db_session(db_path) as conn:
                upsert_multimodal_result(conn, table_name="bulk_results", **flat)

            # 4. Collect Stats for CSV
            row = {
                "destiny": dest,
                "status": "ok",
                "road_cost": flat["road_fuel_cost_r"],
                "mm_cost": flat["total_fuel_cost_r"],
                "delta_cost": flat["delta_cost_r"],
                "savings_pct": res["comparison"]["savings_pct"],
                "road_co2e": flat["road_co2e_kg"],
                "mm_co2e": flat["total_co2e_kg"]
            }
            summary_rows.append(row)
            
            dt = time.time() - t0
            _log.info(f"✅ Done {dest} in {dt:.2f}s. Savings: {row['savings_pct']:.1f}%")
            success_count += 1

        except Exception as e:
            _log.error(f"💥 Failed processing {dest}: {e}")
            fail_count += 1
            summary_rows.append({"destiny": dest, "status": "error", "error_msg": str(e)})

    # End of batch: Write CSV Summary
    if summary_rows:
        keys = summary_rows[0].keys()
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(summary_rows)
        _log.info(f"Summary CSV written to: {output_csv}")

    duration = time.time() - t0_global
    _log.info(f"Batch Complete. Success={success_count}, Fail={fail_count}, Time={duration:.1f}s")


# ────────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk Route Comparison")
    
    # Required
    parser.add_argument("--origin", required=True, help="Fixed Origin")
    parser.add_argument("--dests-file", required=True, type=Path, help="Path to destinations .txt")
    
    # Optional
    parser.add_argument("--cargo", type=float, default=27.0, help="Cargo mass")
    parser.add_argument("--truck", default="semi_27t", help="Truck profile")
    parser.add_argument("--profile", default="driving-hgv", help="Routing profile")
    parser.add_argument("--overwrite", action="store_true", help="Force re-routing")
    parser.add_argument("--output-csv", default="bulk_results_summary.csv", type=Path)
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, type=Path)
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level)

    # Load targets
    try:
        destinations = _load_destinations(args.dests_file)
    except Exception as e:
        _log.critical(str(e))
        return 1
    
    if not destinations:
        _log.warning("Destinations file is empty.")
        return 0

    # Run Loop
    run_bulk(
        origin=args.origin,
        dest_list=destinations,
        cargo_t=args.cargo,
        truck_key=args.truck,
        profile=args.profile,
        overwrite=args.overwrite,
        db_path=args.db_path,
        output_csv=args.output_csv
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())