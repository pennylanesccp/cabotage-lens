from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.addressing.text import ascii_place_key
from modules.infra.db.core import (
    DBConnection,
    bool_to_int,
    current_timestamp_sql,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
    table_columns,
    to_float,
)

DEFAULT_TABLE = "bulk_evaluation_results"

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      scenario_key              TEXT      PRIMARY KEY
    , run_id                    TEXT
    , destination_set_id        TEXT
    , origin_key                TEXT
    , origin_name               TEXT      NOT NULL
    , origin_lat                REAL
    , origin_lon                REAL
    , origin_uf                 TEXT
    , destiny_key               TEXT
    , destiny_name              TEXT      NOT NULL
    , destiny_lat               REAL
    , destiny_lon               REAL
    , destiny_uf                TEXT
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
    , port_origin_name          TEXT
    , port_destiny_name         TEXT
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
    , road_fuel_kg              REAL
    , road_fuel_cost_r          REAL
    , road_co2e_kg              REAL
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
    , emissions_savings_pct     REAL
    , diesel_price_r_per_l      REAL
    , diesel_price_source       TEXT
    , bunker_price_r_per_t      REAL
    , insertion_timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_IDX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_origin_destiny ON {table} (origin_name, destiny_name);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_status ON {table} (status);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_run_id ON {table} (run_id);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_origin_cargo_status ON {table} (origin_key, cargo_t, status);",
)

_OPTIONAL_COLUMNS = (
    ("run_id", "run_id TEXT"),
    ("destination_set_id", "destination_set_id TEXT"),
    ("origin_key", "origin_key TEXT"),
    ("origin_lat", "origin_lat REAL"),
    ("origin_lon", "origin_lon REAL"),
    ("origin_uf", "origin_uf TEXT"),
    ("destiny_key", "destiny_key TEXT"),
    ("destiny_lat", "destiny_lat REAL"),
    ("destiny_lon", "destiny_lon REAL"),
    ("destiny_uf", "destiny_uf TEXT"),
    ("port_origin_name", "port_origin_name TEXT"),
    ("port_destiny_name", "port_destiny_name TEXT"),
    ("emissions_savings_pct", "emissions_savings_pct REAL"),
    ("is_approximation", "is_approximation INTEGER NOT NULL DEFAULT 0"),
    ("route_source", "route_source TEXT"),
    ("approximation_reference_destiny", "approximation_reference_destiny TEXT"),
    ("approximation_reference_distance_km", "approximation_reference_distance_km REAL"),
    ("approximation_delta_straight_line_km", "approximation_delta_straight_line_km REAL"),
    ("approximation_notes", "approximation_notes TEXT"),
)


def _ensure_column(conn: DBConnection, table_name: str, column_name: str, ddl: str) -> None:
    if column_name in table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")



def _backfill_place_keys(conn: DBConnection, table_name: str) -> None:
    rows = conn.execute(
        f"""
        SELECT DISTINCT origin_name, destiny_name
        FROM {table_name}
        WHERE TRIM(COALESCE(origin_name, '')) <> ''
          AND TRIM(COALESCE(destiny_name, '')) <> ''
          AND (
                TRIM(COALESCE(origin_key, '')) = ''
             OR TRIM(COALESCE(destiny_key, '')) = ''
          )
        """
    ).fetchall()
    if not rows:
        return
    updates = [
        (
            ascii_place_key(row[0]),
            ascii_place_key(row[1]),
            row[0],
            row[1],
        )
        for row in rows
    ]
    conn.executemany(
        f"""
        UPDATE {table_name}
           SET origin_key = ?
             , destiny_key = ?
         WHERE origin_name = ?
           AND destiny_name = ?
        """,
        updates,
    )



def ensure_results_table(conn: DBConnection, table_name: str = DEFAULT_TABLE) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "bulk_results", table):
        return
    conn.execute(_DDL_SQL.format(table=table))
    for column_name, ddl in _OPTIONAL_COLUMNS:
        _ensure_column(conn, table, column_name, ddl)
    _backfill_place_keys(conn, table)
    for sql in _IDX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "bulk_results", table)



def upsert_result(
    conn: DBConnection,
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
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
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
    emissions_savings_pct: Optional[float] = None,
    diesel_price_r_per_l: Optional[float] = None,
    diesel_price_source: Optional[str] = None,
    bunker_price_r_per_t: Optional[float] = None,
    run_id: Optional[str] = None,
    destination_set_id: Optional[str] = None,
    origin_key: Optional[str] = None,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    origin_uf: Optional[str] = None,
    destiny_key: Optional[str] = None,
    destiny_lat: Optional[float] = None,
    destiny_lon: Optional[float] = None,
    destiny_uf: Optional[str] = None,
    port_origin_name: Optional[str] = None,
    port_destiny_name: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
) -> None:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)

    sql = f"""
    INSERT INTO {table} (
          scenario_key
        , run_id
        , destination_set_id
        , origin_key
        , origin_name
        , origin_lat
        , origin_lon
        , origin_uf
        , destiny_key
        , destiny_name
        , destiny_lat
        , destiny_lon
        , destiny_uf
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
        , port_origin_name
        , port_destiny_name
        , status
        , error_message
        , geometry_status
        , road_direct_source
        , first_mile_source
        , last_mile_source
        , road_direct_profile_used
        , first_mile_profile_used
        , last_mile_profile_used
        , is_approximation
        , route_source
        , approximation_reference_destiny
        , approximation_reference_distance_km
        , approximation_delta_straight_line_km
        , approximation_notes
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
        , emissions_savings_pct
        , diesel_price_r_per_l
        , diesel_price_source
        , bunker_price_r_per_t
    ) VALUES (
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(scenario_key) DO UPDATE SET
          run_id                    = excluded.run_id
        , destination_set_id        = excluded.destination_set_id
        , origin_key                = excluded.origin_key
        , origin_name               = excluded.origin_name
        , origin_lat                = excluded.origin_lat
        , origin_lon                = excluded.origin_lon
        , origin_uf                 = excluded.origin_uf
        , destiny_key               = excluded.destiny_key
        , destiny_name              = excluded.destiny_name
        , destiny_lat               = excluded.destiny_lat
        , destiny_lon               = excluded.destiny_lon
        , destiny_uf                = excluded.destiny_uf
        , input_origin              = excluded.input_origin
        , input_destiny             = excluded.input_destiny
        , cargo_t                   = excluded.cargo_t
        , truck_key                 = excluded.truck_key
        , ors_profile               = excluded.ors_profile
        , vessel_class              = excluded.vessel_class
        , include_hoteling          = excluded.include_hoteling
        , hoteling_hours_per_call   = excluded.hoteling_hours_per_call
        , port_calls                = excluded.port_calls
        , include_port_ops          = excluded.include_port_ops
        , port_moves_per_call       = excluded.port_moves_per_call
        , cargo_teu                 = excluded.cargo_teu
        , t_per_teu_default         = excluded.t_per_teu_default
        , allocation_mode           = excluded.allocation_mode
        , allocation_load_factor    = excluded.allocation_load_factor
        , full_call_mode            = excluded.full_call_mode
        , port_ops_scenario         = excluded.port_ops_scenario
        , port_origin_name          = excluded.port_origin_name
        , port_destiny_name         = excluded.port_destiny_name
        , status                    = excluded.status
        , error_message             = excluded.error_message
        , geometry_status           = excluded.geometry_status
        , road_direct_source        = excluded.road_direct_source
        , first_mile_source         = excluded.first_mile_source
        , last_mile_source          = excluded.last_mile_source
        , road_direct_profile_used  = excluded.road_direct_profile_used
        , first_mile_profile_used   = excluded.first_mile_profile_used
        , last_mile_profile_used    = excluded.last_mile_profile_used
        , is_approximation          = excluded.is_approximation
        , route_source              = excluded.route_source
        , approximation_reference_destiny = excluded.approximation_reference_destiny
        , approximation_reference_distance_km = excluded.approximation_reference_distance_km
        , approximation_delta_straight_line_km = excluded.approximation_delta_straight_line_km
        , approximation_notes       = excluded.approximation_notes
        , road_distance_km          = excluded.road_distance_km
        , road_fuel_liters          = excluded.road_fuel_liters
        , road_fuel_kg              = excluded.road_fuel_kg
        , road_fuel_cost_r          = excluded.road_fuel_cost_r
        , road_co2e_kg              = excluded.road_co2e_kg
        , mm_road_fuel_liters       = excluded.mm_road_fuel_liters
        , mm_road_fuel_kg           = excluded.mm_road_fuel_kg
        , mm_road_fuel_cost_r       = excluded.mm_road_fuel_cost_r
        , mm_road_co2e_kg           = excluded.mm_road_co2e_kg
        , sea_km                    = excluded.sea_km
        , sea_fuel_kg               = excluded.sea_fuel_kg
        , sea_fuel_cost_r           = excluded.sea_fuel_cost_r
        , sea_co2e_kg               = excluded.sea_co2e_kg
        , total_fuel_kg             = excluded.total_fuel_kg
        , total_fuel_cost_r         = excluded.total_fuel_cost_r
        , total_co2e_kg             = excluded.total_co2e_kg
        , delta_cost_r              = excluded.delta_cost_r
        , delta_co2e_kg             = excluded.delta_co2e_kg
        , savings_pct               = excluded.savings_pct
        , emissions_savings_pct     = excluded.emissions_savings_pct
        , diesel_price_r_per_l      = excluded.diesel_price_r_per_l
        , diesel_price_source       = excluded.diesel_price_source
        , bunker_price_r_per_t      = excluded.bunker_price_r_per_t
        , updated_timestamp         = {current_timestamp_sql()}
    """

    params = (
        scenario_key,
        run_id,
        destination_set_id,
        origin_key,
        origin_name,
        to_float(origin_lat),
        to_float(origin_lon),
        origin_uf,
        destiny_key,
        destiny_name,
        to_float(destiny_lat),
        to_float(destiny_lon),
        destiny_uf,
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
        port_origin_name,
        port_destiny_name,
        status,
        error_message,
        geometry_status,
        road_direct_source,
        first_mile_source,
        last_mile_source,
        road_direct_profile_used,
        first_mile_profile_used,
        last_mile_profile_used,
        bool_to_int(is_approximation),
        route_source,
        approximation_reference_destiny,
        to_float(approximation_reference_distance_km),
        to_float(approximation_delta_straight_line_km),
        approximation_notes,
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
        to_float(emissions_savings_pct),
        to_float(diesel_price_r_per_l),
        diesel_price_source,
        to_float(bunker_price_r_per_t),
    )
    conn.execute(sql, params)
