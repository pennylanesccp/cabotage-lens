from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.addressing.text import ascii_place_key
from modules.infra.db.bulk_runs import BulkRunSelector
from modules.infra.db.core import (
    DBConnection,
    bool_to_int,
    current_timestamp_sql,
    int_to_bool,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
    table_columns,
    to_float,
)

DEFAULT_TABLE = "bulk_evaluation_results"
_FLOAT_TOLERANCE = 1e-9

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


@dataclass(frozen=True)
class BulkResultRecord:
    scenario_key: str
    run_id: Optional[str]
    destination_set_id: Optional[str]
    origin_key: Optional[str]
    origin_name: str
    destiny_name: str
    input_destiny: str
    cargo_t: float
    truck_key: str
    ors_profile: str
    vessel_class: Optional[str]
    include_hoteling: bool
    hoteling_hours_per_call: Optional[float]
    port_calls: Optional[int]
    include_port_ops: bool
    port_moves_per_call: Optional[float]
    cargo_teu: Optional[float]
    t_per_teu_default: Optional[float]
    allocation_mode: Optional[str]
    allocation_load_factor: Optional[float]
    full_call_mode: bool
    port_ops_scenario: Optional[str]
    status: str
    error_message: Optional[str]
    destiny_lat: Optional[float]
    destiny_lon: Optional[float]
    destiny_uf: Optional[str]
    port_destiny_name: Optional[str]
    road_fuel_cost_r: Optional[float]
    total_fuel_cost_r: Optional[float]
    delta_cost_r: Optional[float]
    savings_pct: Optional[float]
    road_co2e_kg: Optional[float]
    total_co2e_kg: Optional[float]
    delta_co2e_kg: Optional[float]
    emissions_savings_pct: Optional[float]
    road_distance_km: Optional[float]
    sea_km: Optional[float]
    is_approximation: bool
    route_source: Optional[str]
    updated_timestamp: Any


@dataclass(frozen=True)
class BulkResultSummary:
    row_count: int
    success_count: int
    fail_count: int
    latest_updated_timestamp: Any
    latest_run_id: Optional[str]


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _nullable_clause(column: str, value: Any, *, params: list[Any], clauses: list[str], numeric: bool = False) -> None:
    if value is None:
        clauses.append(f"{column} IS NULL")
        return
    if numeric:
        clauses.append(f"ABS({column} - ?) <= ?")
        params.extend((float(value), _FLOAT_TOLERANCE))
        return
    clauses.append(f"{column} = ?")
    params.append(value)


def _selector_clauses(selector: BulkRunSelector) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    _nullable_clause("origin_key", selector.origin_key, params=params, clauses=clauses)
    _nullable_clause("cargo_t", selector.cargo_t, params=params, clauses=clauses, numeric=True)
    _nullable_clause("truck_key", selector.truck_key, params=params, clauses=clauses)
    _nullable_clause("ors_profile", selector.ors_profile, params=params, clauses=clauses)
    _nullable_clause("vessel_class", selector.vessel_class, params=params, clauses=clauses)
    _nullable_clause("include_hoteling", bool_to_int(selector.include_hoteling), params=params, clauses=clauses)
    _nullable_clause(
        "hoteling_hours_per_call",
        selector.hoteling_hours_per_call,
        params=params,
        clauses=clauses,
        numeric=True,
    )
    _nullable_clause("port_calls", int(selector.port_calls), params=params, clauses=clauses)
    _nullable_clause("include_port_ops", bool_to_int(selector.include_port_ops), params=params, clauses=clauses)
    _nullable_clause(
        "port_moves_per_call",
        selector.port_moves_per_call,
        params=params,
        clauses=clauses,
        numeric=True,
    )
    _nullable_clause("cargo_teu", selector.cargo_teu, params=params, clauses=clauses, numeric=True)
    _nullable_clause(
        "t_per_teu_default",
        selector.t_per_teu_default,
        params=params,
        clauses=clauses,
        numeric=True,
    )
    _nullable_clause("allocation_mode", selector.allocation_mode, params=params, clauses=clauses)
    _nullable_clause(
        "allocation_load_factor",
        selector.allocation_load_factor,
        params=params,
        clauses=clauses,
        numeric=True,
    )
    _nullable_clause("full_call_mode", bool_to_int(selector.full_call_mode), params=params, clauses=clauses)
    _nullable_clause("port_ops_scenario", selector.port_ops_scenario, params=params, clauses=clauses)
    _nullable_clause("destination_set_id", selector.destination_set_id, params=params, clauses=clauses)
    return clauses, params


def _row_to_result_record(row: Sequence[Any]) -> BulkResultRecord:
    return BulkResultRecord(
        scenario_key=str(row[0]),
        run_id=_normalize_text(row[1]),
        destination_set_id=_normalize_text(row[2]),
        origin_key=_normalize_text(row[3]),
        origin_name=str(row[4]),
        destiny_name=str(row[5]),
        input_destiny=str(row[6]),
        cargo_t=float(row[7]),
        truck_key=str(row[8]),
        ors_profile=str(row[9]),
        vessel_class=_normalize_text(row[10]),
        include_hoteling=bool(int_to_bool(row[11])),
        hoteling_hours_per_call=to_float(row[12]),
        port_calls=_safe_int(row[13], default=0) if row[13] is not None else None,
        include_port_ops=bool(int_to_bool(row[14])),
        port_moves_per_call=to_float(row[15]),
        cargo_teu=to_float(row[16]),
        t_per_teu_default=to_float(row[17]),
        allocation_mode=_normalize_text(row[18]),
        allocation_load_factor=to_float(row[19]),
        full_call_mode=bool(int_to_bool(row[20])),
        port_ops_scenario=_normalize_text(row[21]),
        status=str(row[22]),
        error_message=_normalize_text(row[23]),
        destiny_lat=to_float(row[24]),
        destiny_lon=to_float(row[25]),
        destiny_uf=_normalize_text(row[26]),
        port_destiny_name=_normalize_text(row[27]),
        road_fuel_cost_r=to_float(row[28]),
        total_fuel_cost_r=to_float(row[29]),
        delta_cost_r=to_float(row[30]),
        savings_pct=to_float(row[31]),
        road_co2e_kg=to_float(row[32]),
        total_co2e_kg=to_float(row[33]),
        delta_co2e_kg=to_float(row[34]),
        emissions_savings_pct=to_float(row[35]),
        road_distance_km=to_float(row[36]),
        sea_km=to_float(row[37]),
        is_approximation=bool(int_to_bool(row[38])),
        route_source=_normalize_text(row[39]),
        updated_timestamp=row[40],
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


def summarize_results(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    table_name: str = DEFAULT_TABLE,
) -> BulkResultSummary:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)
    clauses, params = _selector_clauses(selector)
    where = " AND ".join(clauses) if clauses else "1=1"
    row = conn.execute(
        f"""
        SELECT
              COUNT(*) AS row_count
            , SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS success_count
            , SUM(CASE WHEN status <> 'ok' THEN 1 ELSE 0 END) AS fail_count
            , MAX(updated_timestamp) AS latest_updated_timestamp
            , (
                SELECT run_id
                FROM {table} AS latest_row
                WHERE {where}
                ORDER BY updated_timestamp DESC, insertion_timestamp DESC
                LIMIT 1
              ) AS latest_run_id
        FROM {table}
        WHERE {where}
        """,
        params + params,
    ).fetchone()
    if not row:
        return BulkResultSummary(
            row_count=0,
            success_count=0,
            fail_count=0,
            latest_updated_timestamp=None,
            latest_run_id=None,
        )
    return BulkResultSummary(
        row_count=_safe_int(row[0]),
        success_count=_safe_int(row[1]),
        fail_count=_safe_int(row[2]),
        latest_updated_timestamp=row[3],
        latest_run_id=_normalize_text(row[4]),
    )


def list_results(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    only_success: Optional[bool] = None,
    table_name: str = DEFAULT_TABLE,
) -> List[BulkResultRecord]:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)
    clauses, params = _selector_clauses(selector)
    if only_success is True:
        clauses.append("status = ?")
        params.append("ok")
    elif only_success is False:
        clauses.append("status <> ?")
        params.append("ok")
    where = " AND ".join(clauses) if clauses else "1=1"
    rows = conn.execute(
        f"""
        SELECT
              scenario_key
            , run_id
            , destination_set_id
            , origin_key
            , origin_name
            , destiny_name
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
            , destiny_lat
            , destiny_lon
            , destiny_uf
            , port_destiny_name
            , road_fuel_cost_r
            , total_fuel_cost_r
            , delta_cost_r
            , savings_pct
            , road_co2e_kg
            , total_co2e_kg
            , delta_co2e_kg
            , emissions_savings_pct
            , road_distance_km
            , sea_km
            , is_approximation
            , route_source
            , updated_timestamp
        FROM {table}
        WHERE {where}
        ORDER BY destiny_name ASC, updated_timestamp DESC
        """,
        params,
    ).fetchall()
    return [_row_to_result_record(row) for row in rows]


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
