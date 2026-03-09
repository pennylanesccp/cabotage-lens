# modules/infra/db/multimodal.py
# -*- coding: utf-8 -*-

"""
Multimodal Results (DDL & DML).
===============================

Manages analytical tables storing the final comparison:
Road Only vs. Multimodal (Cabotage).

Note: Tables are dynamically named (for example `analysis_results`) and now
work on both Postgres and legacy SQLite.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.core import DBConnection, mark_schema_ready, safe_table_name, schema_is_ready, to_float
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
    , road_fuel_kg        REAL
    , road_fuel_cost_r    REAL
    , road_co2e_kg        REAL
    
    -- Multimodal Path
    , mm_road_fuel_liters REAL
    , mm_road_fuel_kg     REAL
    , mm_road_fuel_cost_r REAL
    , mm_road_co2e_kg     REAL
    , sea_km              REAL
    , sea_fuel_kg         REAL
    , sea_fuel_cost_r     REAL
    , sea_co2e_kg         REAL
    
    -- Totals & Deltas
    , total_fuel_cost_r   REAL
    , total_co2e_kg       REAL
    , total_fuel_kg       REAL
    , delta_cost_r        REAL
    , delta_co2e_kg       REAL
    
    , insertion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_dest 
    ON {table} (destiny_name);
"""

def ensure_results_table(conn: DBConnection, table_name: str) -> None:
    """Create a specific results table."""
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "multimodal_results", table):
        return
    conn.execute(_DDL_SQL.format(table=table))
    conn.execute(_IDX_SQL.format(table=table))
    mark_schema_ready(conn, "multimodal_results", table)


# ────────────────────────────────────────────────────────────────────────────────
# Write Operations
# ────────────────────────────────────────────────────────────────────────────────

def upsert_result(
      conn: DBConnection
    , table_name: str
    , *
    , origin_name: str
    , destiny_name: str
    , cargo_t: float
    
    # Road Baseline
    , road_distance_km: Optional[float] = None
    , road_fuel_liters: Optional[float] = None
    , road_fuel_kg: Optional[float] = None
    , road_fuel_cost_r: Optional[float] = None
    , road_co2e_kg: Optional[float] = None
    
    # Multimodal Road
    , mm_road_fuel_liters: Optional[float] = None
    , mm_road_fuel_kg: Optional[float] = None
    , mm_road_fuel_cost_r: Optional[float] = None
    , mm_road_co2e_kg: Optional[float] = None
    
    # Multimodal Sea
    , sea_km: Optional[float] = None
    , sea_fuel_kg: Optional[float] = None
    , sea_fuel_cost_r: Optional[float] = None
    , sea_co2e_kg: Optional[float] = None
    
    # Totals
    , total_fuel_kg: Optional[float] = None
    , total_fuel_cost_r: Optional[float] = None
    , total_co2e_kg: Optional[float] = None
    
    # Deltas
    , delta_cost_r: Optional[float] = None
    , delta_co2e_kg: Optional[float] = None
) -> None:
    """
    Insert comparison result. 
    """
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)

    sql = f"""
    INSERT INTO {table} (
          origin_name, destiny_name, cargo_t
        , road_distance_km, road_fuel_liters, road_fuel_kg, road_fuel_cost_r, road_co2e_kg
        , mm_road_fuel_liters, mm_road_fuel_kg, mm_road_fuel_cost_r, mm_road_co2e_kg
        , sea_km, sea_fuel_kg, sea_fuel_cost_r, sea_co2e_kg
        , total_fuel_kg, total_fuel_cost_r, total_co2e_kg
        , delta_cost_r, delta_co2e_kg
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(destiny_name) DO UPDATE SET
          origin_name         = excluded.origin_name
        , cargo_t             = excluded.cargo_t
        , road_distance_km    = excluded.road_distance_km
        , road_fuel_liters    = excluded.road_fuel_liters
        , road_fuel_kg        = excluded.road_fuel_kg
        , road_fuel_cost_r    = excluded.road_fuel_cost_r
        , road_co2e_kg        = excluded.road_co2e_kg
        , mm_road_fuel_liters = excluded.mm_road_fuel_liters
        , mm_road_fuel_kg     = excluded.mm_road_fuel_kg
        , mm_road_fuel_cost_r = excluded.mm_road_fuel_cost_r
        , mm_road_co2e_kg     = excluded.mm_road_co2e_kg
        , sea_km              = excluded.sea_km
        , sea_fuel_kg         = excluded.sea_fuel_kg
        , sea_fuel_cost_r     = excluded.sea_fuel_cost_r
        , sea_co2e_kg         = excluded.sea_co2e_kg
        , total_fuel_kg       = excluded.total_fuel_kg
        , total_fuel_cost_r   = excluded.total_fuel_cost_r
        , total_co2e_kg       = excluded.total_co2e_kg
        , delta_cost_r        = excluded.delta_cost_r
        , delta_co2e_kg       = excluded.delta_co2e_kg
    """
    
    params = (
        origin_name, destiny_name, to_float(cargo_t),
        to_float(road_distance_km), to_float(road_fuel_liters), to_float(road_fuel_kg), to_float(road_fuel_cost_r), to_float(road_co2e_kg),
        to_float(mm_road_fuel_liters), to_float(mm_road_fuel_kg), to_float(mm_road_fuel_cost_r), to_float(mm_road_co2e_kg),
        to_float(sea_km), to_float(sea_fuel_kg), to_float(sea_fuel_cost_r), to_float(sea_co2e_kg),
        to_float(total_fuel_kg), to_float(total_fuel_cost_r), to_float(total_co2e_kg),
        to_float(delta_cost_r), to_float(delta_co2e_kg)
    )
    conn.execute(sql, params)


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.db.core import db_session
    print("--- Multimodal DB Smoke Test ---")
    
    with db_session("smoke_test_multimodal.sqlite", backend="sqlite") as conn:
        upsert_result(
            conn, "test_results",
            origin_name="SP", destiny_name="RJ", cargo_t=10,
            road_distance_km=400, road_fuel_cost_r=1000, delta_cost_r=-200,
            road_fuel_kg=150.0
        )
        print("Upsert successful.")
    Path("smoke_test_multimodal.sqlite").unlink(missing_ok=True)
    print("--- Done ---")
