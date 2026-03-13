from __future__ import annotations

from typing import Optional

from modules.infra.db.core import DBConnection, mark_schema_ready, safe_table_name, schema_is_ready, to_float

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_name         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , cargo_t             REAL      NOT NULL
    , road_distance_km    REAL
    , road_fuel_liters    REAL
    , road_fuel_kg        REAL
    , road_fuel_cost_r    REAL
    , road_co2e_kg        REAL
    , mm_road_fuel_liters REAL
    , mm_road_fuel_kg     REAL
    , mm_road_fuel_cost_r REAL
    , mm_road_co2e_kg     REAL
    , sea_km              REAL
    , sea_fuel_kg         REAL
    , sea_fuel_cost_r     REAL
    , sea_co2e_kg         REAL
    , total_fuel_cost_r   REAL
    , total_co2e_kg       REAL
    , total_fuel_kg       REAL
    , delta_cost_r        REAL
    , delta_co2e_kg       REAL
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_dest
    ON {table} (destiny_name);
"""


def ensure_results_table(conn: DBConnection, table_name: str) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "multimodal_results", table):
        return
    conn.execute(_DDL_SQL.format(table=table))
    conn.execute(_IDX_SQL.format(table=table))
    mark_schema_ready(conn, "multimodal_results", table)


def upsert_result(
    conn: DBConnection,
    table_name: str,
    *,
    origin_name: str,
    destiny_name: str,
    cargo_t: float,
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
) -> None:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)

    conn.execute(
        f"""
        INSERT INTO {table} (
              origin_name
            , destiny_name
            , cargo_t
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
        """,
        (
            origin_name,
            destiny_name,
            to_float(cargo_t),
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
        ),
    )
