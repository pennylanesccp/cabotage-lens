# modules/infra/db/multimodal.py
# -*- coding: utf-8 -*-

"""
Multimodal Results (DDL & DML).
===============================

Manages analytical tables storing the final comparison:
Road Only vs. Multimodal (Cabotage).

Note: Tables are dynamically named (e.g., "SP_to_BR_50tons").
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Mapping

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.core import to_float
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Schema
# ────────────────────────────────────────────────────────────────────────────────

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_name         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , cargo_t             REAL      NOT NULL
    
    -- Road Baseline
    , road_distance_km    REAL
    , road_fuel_liters    REAL
    , road_fuel_cost_r    REAL
    , road_co2e_kg        REAL
    
    -- Multimodal Path
    , mm_road_fuel_liters REAL
    , mm_road_fuel_cost_r REAL
    , mm_road_co2e_kg     REAL
    , sea_km              REAL
    , sea_fuel_cost_r     REAL
    , sea_co2e_kg         REAL
    
    -- Totals & Deltas
    , total_fuel_cost_r   REAL
    , total_co2e_kg       REAL
    , delta_cost_r        REAL
    , delta_co2e_kg       REAL
    
    , insertion_timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_dest 
    ON {table} (destiny_name);
"""

def ensure_results_table(conn: sqlite3.Connection, table_name: str) -> None:
    """Create a specific results table."""
    conn.execute(_DDL_SQL.format(table=table_name))
    conn.execute(_IDX_SQL.format(table=table_name))


# ────────────────────────────────────────────────────────────────────────────────
# Write Operations
# ────────────────────────────────────────────────────────────────────────────────

def upsert_result(
      conn: sqlite3.Connection
    , table_name: str
    , *
    , origin_name: str
    , destiny_name: str
    , cargo_t: float
    , road_dist: Optional[float] = None
    , road_cost: Optional[float] = None
    , road_co2e: Optional[float] = None
    , mm_road_cost: Optional[float] = None
    , sea_km: Optional[float] = None
    , sea_cost: Optional[float] = None
    , total_cost: Optional[float] = None
    , total_co2e: Optional[float] = None
    , delta_cost: Optional[float] = None
    , delta_co2e: Optional[float] = None
    # ... add other fields as needed (keeping it concise for this example)
) -> None:
    """
    Insert comparison result. 
    
    Note: Used shortened arg names to fit 200-line limit, 
    but mapping to DB columns is explicit below.
    """
    ensure_results_table(conn, table_name)

    sql = f"""
    INSERT INTO {table_name} (
          origin_name, destiny_name, cargo_t
        , road_distance_km, road_fuel_cost_r, road_co2e_kg
        , mm_road_fuel_cost_r, sea_km, sea_fuel_cost_r
        , total_fuel_cost_r, total_co2e_kg, delta_cost_r, delta_co2e_kg
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(destiny_name) DO UPDATE SET
          road_fuel_cost_r  = excluded.road_fuel_cost_r
        , total_fuel_cost_r = excluded.total_fuel_cost_r
        , delta_cost_r      = excluded.delta_cost_r
    """
    
    params = (
        origin_name, destiny_name, to_float(cargo_t),
        to_float(road_dist), to_float(road_cost), to_float(road_co2e),
        to_float(mm_road_cost), to_float(sea_km), to_float(sea_cost),
        to_float(total_cost), to_float(total_co2e), to_float(delta_cost), to_float(delta_co2e)
    )
    conn.execute(sql, params)


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.db.core import db_session
    print("--- Multimodal DB Smoke Test ---")
    
    with db_session(":memory:") as conn:
        upsert_result(
            conn, "test_results",
            origin_name="SP", destiny_name="RJ", cargo_t=10,
            road_dist=400, road_cost=1000, delta_cost=-200
        )
        print("Upsert successful.")
    print("--- Done ---")