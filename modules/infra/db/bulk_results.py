# modules/infra/db/bulk_results.py
# -*- coding: utf-8 -*-

"""
Bulk evaluation result persistence.

Stores analytical outputs for bulk multimodal comparisons. These rows are not a
routing cache and are safe to recompute and upsert on reruns.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.core import bool_to_int, to_float

DEFAULT_TABLE = "bulk_evaluation_results"

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      scenario_key              TEXT      PRIMARY KEY
    , origin_name               TEXT      NOT NULL
    , destiny_name              TEXT      NOT NULL
    , input_origin              TEXT      NOT NULL
    , input_destiny             TEXT      NOT NULL
    , cargo_t                   REAL      NOT NULL
    , truck_key                 TEXT      NOT NULL
    , ors_profile               TEXT      NOT NULL
    , vessel_class              TEXT
    , include_hoteling          INTEGER   NOT NULL DEFAULT 1
    , hoteling_hours_per_call   REAL
    , port_calls                INTEGER
    , include_port_ops          INTEGER   NOT NULL DEFAULT 1
    , port_moves_per_call       REAL
    , cargo_teu                 REAL
    , t_per_teu_default         REAL
    , allocation_mode           TEXT
    , allocation_load_factor    REAL
    , full_call_mode            INTEGER   NOT NULL DEFAULT 0
    , port_ops_scenario         TEXT
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , geometry_status           TEXT
    , road_direct_source        TEXT
    , first_mile_source         TEXT
    , last_mile_source          TEXT
    , road_direct_profile_used  TEXT
    , first_mile_profile_used   TEXT
    , last_mile_profile_used    TEXT
    , road_distance_km          REAL
    , road_fuel_liters          REAL
    , road_fuel_kg             REAL
    , road_fuel_cost_r          REAL
    , road_co2e_kg             REAL
    , mm_road_fuel_liters       REAL
    , mm_road_fuel_kg           REAL
    , mm_road_fuel_cost_r       REAL
    , mm_road_co2e_kg           REAL
    , sea_km                    REAL
    , sea_fuel_kg               REAL
    , sea_fuel_cost_r           REAL
    , sea_co2e_kg               REAL
    , total_fuel_kg             REAL
    , total_fuel_cost_r         REAL
    , total_co2e_kg             REAL
    , delta_cost_r              REAL
    , delta_co2e_kg             REAL
    , savings_pct               REAL
    , diesel_price_r_per_l      REAL
    , diesel_price_source       TEXT
    , bunker_price_r_per_t      REAL
    , insertion_timestamp       TIMESTAMP NOT NULL DEFAULT (datetime('now'))
    , updated_timestamp         TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
"""

_IDX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_origin_destiny ON {table} (origin_name, destiny_name);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_status ON {table} (status);",
)


def ensure_results_table(conn: sqlite3.Connection, table_name: str = DEFAULT_TABLE) -> None:
    conn.execute(_DDL_SQL.format(table=table_name))
    for sql in _IDX_SQL:
        conn.execute(sql.format(table=table_name))


def upsert_result(
    conn: sqlite3.Connection,
    *,
    scenario_key: str,
    origin_name: str,
    destiny_name: str,
    input_origin: str,
    input_destiny: str,
    cargo_t: float,
    truck_key: str,
    ors_profile: str,
    vessel_class: Optional[str] = None,
    include_hoteling: bool = True,
    hoteling_hours_per_call: Optional[float] = None,
    port_calls: Optional[int] = None,
    include_port_ops: bool = True,
    port_moves_per_call: Optional[float] = None,
    cargo_teu: Optional[float] = None,
    t_per_teu_default: Optional[float] = None,
    allocation_mode: Optional[str] = None,
    allocation_load_factor: Optional[float] = None,
    full_call_mode: bool = False,
    port_ops_scenario: Optional[str] = None,
    status: str = "ok",
    error_message: Optional[str] = None,
    geometry_status: Optional[str] = None,
    road_direct_source: Optional[str] = None,
    first_mile_source: Optional[str] = None,
    last_mile_source: Optional[str] = None,
    road_direct_profile_used: Optional[str] = None,
    first_mile_profile_used: Optional[str] = None,
    last_mile_profile_used: Optional[str] = None,
    road_distance_km: Optional[float] = None,
    road_fuel_liters: Optional[float] = None,
    road_fuel_kg: Optional[float] = None,
    road_fuel_cost_r: Optional[float] = None,
    road_co2e_kg: Optional[float] = None,
    mm_road_fuel_liters: Optional[float] = None,
    mm_road_fuel_kg: Optional[float] = None,
    mm_road_fuel_cost_r: Optional[float] = None,
    mm_road_co2e_kg: Optional[float] = None,
    sea_km: Optional[float] = None,
    sea_fuel_kg: Optional[float] = None,
    sea_fuel_cost_r: Optional[float] = None,
    sea_co2e_kg: Optional[float] = None,
    total_fuel_kg: Optional[float] = None,
    total_fuel_cost_r: Optional[float] = None,
    total_co2e_kg: Optional[float] = None,
    delta_cost_r: Optional[float] = None,
    delta_co2e_kg: Optional[float] = None,
    savings_pct: Optional[float] = None,
    diesel_price_r_per_l: Optional[float] = None,
    diesel_price_source: Optional[str] = None,
    bunker_price_r_per_t: Optional[float] = None,
    table_name: str = DEFAULT_TABLE,
) -> None:
    ensure_results_table(conn, table_name)

    sql = f"""
    INSERT INTO {table_name} (
          scenario_key
        , origin_name
        , destiny_name
        , input_origin
        , input_destiny
        , cargo_t
        , truck_key
        , ors_profile
        , vessel_class
        , include_hoteling
        , hoteling_hours_per_call
        , port_calls
        , include_port_ops
        , port_moves_per_call
        , cargo_teu
        , t_per_teu_default
        , allocation_mode
        , allocation_load_factor
        , full_call_mode
        , port_ops_scenario
        , status
        , error_message
        , geometry_status
        , road_direct_source
        , first_mile_source
        , last_mile_source
        , road_direct_profile_used
        , first_mile_profile_used
        , last_mile_profile_used
        , road_distance_km
        , road_fuel_liters
        , road_fuel_kg
        , road_fuel_cost_r
        , road_co2e_kg
        , mm_road_fuel_liters
        , mm_road_fuel_kg
        , mm_road_fuel_cost_r
        , mm_road_co2e_kg
        , sea_km
        , sea_fuel_kg
        , sea_fuel_cost_r
        , sea_co2e_kg
        , total_fuel_kg
        , total_fuel_cost_r
        , total_co2e_kg
        , delta_cost_r
        , delta_co2e_kg
        , savings_pct
        , diesel_price_r_per_l
        , diesel_price_source
        , bunker_price_r_per_t
    ) VALUES (
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(scenario_key) DO UPDATE SET
          origin_name              = excluded.origin_name
        , destiny_name             = excluded.destiny_name
        , input_origin             = excluded.input_origin
        , input_destiny            = excluded.input_destiny
        , cargo_t                  = excluded.cargo_t
        , truck_key                = excluded.truck_key
        , ors_profile              = excluded.ors_profile
        , vessel_class             = excluded.vessel_class
        , include_hoteling         = excluded.include_hoteling
        , hoteling_hours_per_call  = excluded.hoteling_hours_per_call
        , port_calls               = excluded.port_calls
        , include_port_ops         = excluded.include_port_ops
        , port_moves_per_call      = excluded.port_moves_per_call
        , cargo_teu                = excluded.cargo_teu
        , t_per_teu_default        = excluded.t_per_teu_default
        , allocation_mode          = excluded.allocation_mode
        , allocation_load_factor   = excluded.allocation_load_factor
        , full_call_mode           = excluded.full_call_mode
        , port_ops_scenario        = excluded.port_ops_scenario
        , status                   = excluded.status
        , error_message            = excluded.error_message
        , geometry_status          = excluded.geometry_status
        , road_direct_source       = excluded.road_direct_source
        , first_mile_source        = excluded.first_mile_source
        , last_mile_source         = excluded.last_mile_source
        , road_direct_profile_used = excluded.road_direct_profile_used
        , first_mile_profile_used  = excluded.first_mile_profile_used
        , last_mile_profile_used   = excluded.last_mile_profile_used
        , road_distance_km         = excluded.road_distance_km
        , road_fuel_liters         = excluded.road_fuel_liters
        , road_fuel_kg             = excluded.road_fuel_kg
        , road_fuel_cost_r         = excluded.road_fuel_cost_r
        , road_co2e_kg             = excluded.road_co2e_kg
        , mm_road_fuel_liters      = excluded.mm_road_fuel_liters
        , mm_road_fuel_kg          = excluded.mm_road_fuel_kg
        , mm_road_fuel_cost_r      = excluded.mm_road_fuel_cost_r
        , mm_road_co2e_kg          = excluded.mm_road_co2e_kg
        , sea_km                   = excluded.sea_km
        , sea_fuel_kg              = excluded.sea_fuel_kg
        , sea_fuel_cost_r          = excluded.sea_fuel_cost_r
        , sea_co2e_kg              = excluded.sea_co2e_kg
        , total_fuel_kg            = excluded.total_fuel_kg
        , total_fuel_cost_r        = excluded.total_fuel_cost_r
        , total_co2e_kg            = excluded.total_co2e_kg
        , delta_cost_r             = excluded.delta_cost_r
        , delta_co2e_kg            = excluded.delta_co2e_kg
        , savings_pct              = excluded.savings_pct
        , diesel_price_r_per_l     = excluded.diesel_price_r_per_l
        , diesel_price_source      = excluded.diesel_price_source
        , bunker_price_r_per_t     = excluded.bunker_price_r_per_t
        , updated_timestamp        = datetime('now')
    """

    params = (
        scenario_key,
        origin_name,
        destiny_name,
        input_origin,
        input_destiny,
        to_float(cargo_t),
        truck_key,
        ors_profile,
        vessel_class,
        bool_to_int(include_hoteling),
        to_float(hoteling_hours_per_call),
        port_calls,
        bool_to_int(include_port_ops),
        to_float(port_moves_per_call),
        to_float(cargo_teu),
        to_float(t_per_teu_default),
        allocation_mode,
        to_float(allocation_load_factor),
        bool_to_int(full_call_mode),
        port_ops_scenario,
        status,
        error_message,
        geometry_status,
        road_direct_source,
        first_mile_source,
        last_mile_source,
        road_direct_profile_used,
        first_mile_profile_used,
        last_mile_profile_used,
        to_float(road_distance_km),
        to_float(road_fuel_liters),
        to_float(road_fuel_kg),
        to_float(road_fuel_cost_r),
        to_float(road_co2e_kg),
        to_float(mm_road_fuel_liters),
        to_float(mm_road_fuel_kg),
        to_float(mm_road_fuel_cost_r),
        to_float(mm_road_co2e_kg),
        to_float(sea_km),
        to_float(sea_fuel_kg),
        to_float(sea_fuel_cost_r),
        to_float(sea_co2e_kg),
        to_float(total_fuel_kg),
        to_float(total_fuel_cost_r),
        to_float(total_co2e_kg),
        to_float(delta_cost_r),
        to_float(delta_co2e_kg),
        to_float(savings_pct),
        to_float(diesel_price_r_per_l),
        diesel_price_source,
        to_float(bunker_price_r_per_t),
    )
    conn.execute(sql, params)
