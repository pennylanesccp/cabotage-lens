from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

DEFAULT_RUNS_TABLE = "bulk_evaluation_runs"
DEFAULT_RUN_RESULTS_TABLE = "bulk_evaluation_run_results"
_FLOAT_TOLERANCE = 1e-9

_RUNS_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      run_id                    TEXT      PRIMARY KEY
    , origin_key                TEXT      NOT NULL
    , origin_name               TEXT      NOT NULL
    , input_origin              TEXT      NOT NULL
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
    , destination_set_id        TEXT      NOT NULL
    , destination_count         INTEGER   NOT NULL DEFAULT 0
    , success_count             INTEGER   NOT NULL DEFAULT 0
    , fail_count                INTEGER   NOT NULL DEFAULT 0
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , duration_s                REAL
    , started_timestamp         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , completed_timestamp       TIMESTAMP
    , updated_timestamp         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_RUN_RESULTS_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      run_id                    TEXT      NOT NULL
    , scenario_key              TEXT      NOT NULL
    , origin_key                TEXT      NOT NULL
    , origin_name               TEXT      NOT NULL
    , origin_lat                REAL
    , origin_lon                REAL
    , origin_uf                 TEXT
    , destiny_key               TEXT      NOT NULL
    , destiny_name              TEXT      NOT NULL
    , destiny_lat               REAL
    , destiny_lon               REAL
    , destiny_uf                TEXT
    , input_origin              TEXT      NOT NULL
    , input_destiny             TEXT      NOT NULL
    , destination_set_id        TEXT      NOT NULL
    , port_origin_name          TEXT
    , port_destiny_name         TEXT
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , road_cost_r               REAL
    , multimodal_cost_r         REAL
    , cost_delta_r              REAL
    , cost_savings_pct          REAL
    , road_emissions_kg         REAL
    , multimodal_emissions_kg   REAL
    , emissions_delta_kg        REAL
    , emissions_savings_pct     REAL
    , road_distance_km          REAL
    , sea_km                    REAL
    , insertion_timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , PRIMARY KEY (run_id, scenario_key)
);
"""

_RUNS_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_selector ON {table} (origin_key, cargo_t, destination_set_id, status, updated_timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_status ON {table} (status);",
)

_RUN_RESULTS_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_run_status ON {table} (run_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_coords ON {table} (run_id, destiny_lat, destiny_lon);",
)

_RUN_RESULTS_OPTIONAL_COLUMNS = (
    ("is_approximation", "is_approximation INTEGER NOT NULL DEFAULT 0"),
    ("route_source", "route_source TEXT"),
    ("approximation_reference_destiny", "approximation_reference_destiny TEXT"),
    ("approximation_reference_distance_km", "approximation_reference_distance_km REAL"),
    ("approximation_delta_straight_line_km", "approximation_delta_straight_line_km REAL"),
    ("approximation_notes", "approximation_notes TEXT"),
)


@dataclass(frozen=True)
class BulkRunSelector:
    origin_key: str
    cargo_t: float
    truck_key: str
    ors_profile: str
    vessel_class: Optional[str]
    include_hoteling: bool
    hoteling_hours_per_call: float
    port_calls: int
    include_port_ops: bool
    port_moves_per_call: Optional[float]
    cargo_teu: Optional[float]
    t_per_teu_default: float
    allocation_mode: Optional[str]
    allocation_load_factor: float
    full_call_mode: bool
    port_ops_scenario: str
    destination_set_id: str


@dataclass(frozen=True)
class BulkRunRecord:
    run_id: str
    origin_key: str
    origin_name: str
    input_origin: str
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
    destination_set_id: str
    destination_count: int
    success_count: int
    fail_count: int
    status: str
    error_message: Optional[str]
    duration_s: Optional[float]
    started_timestamp: Any
    completed_timestamp: Any
    updated_timestamp: Any


@dataclass(frozen=True)
class BulkRunResultRecord:
    run_id: str
    scenario_key: str
    origin_key: str
    origin_name: str
    origin_lat: Optional[float]
    origin_lon: Optional[float]
    origin_uf: Optional[str]
    destiny_key: str
    destiny_name: str
    destiny_lat: Optional[float]
    destiny_lon: Optional[float]
    destiny_uf: Optional[str]
    input_origin: str
    input_destiny: str
    destination_set_id: str
    port_origin_name: Optional[str]
    port_destiny_name: Optional[str]
    status: str
    error_message: Optional[str]
    road_cost_r: Optional[float]
    multimodal_cost_r: Optional[float]
    cost_delta_r: Optional[float]
    cost_savings_pct: Optional[float]
    road_emissions_kg: Optional[float]
    multimodal_emissions_kg: Optional[float]
    emissions_delta_kg: Optional[float]
    emissions_savings_pct: Optional[float]
    road_distance_km: Optional[float]
    sea_km: Optional[float]
    is_approximation: bool
    route_source: Optional[str]
    approximation_reference_destiny: Optional[str]
    approximation_reference_distance_km: Optional[float]
    approximation_delta_straight_line_km: Optional[float]
    approximation_notes: Optional[str]
    insertion_timestamp: Any
    updated_timestamp: Any


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


def _ensure_column(conn: DBConnection, table_name: str, column_name: str, ddl: str) -> None:
    if column_name in table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


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


def _row_to_run_record(row: Sequence[Any]) -> BulkRunRecord:
    return BulkRunRecord(
        run_id=str(row[0]),
        origin_key=str(row[1]),
        origin_name=str(row[2]),
        input_origin=str(row[3]),
        cargo_t=float(row[4]),
        truck_key=str(row[5]),
        ors_profile=str(row[6]),
        vessel_class=_normalize_text(row[7]),
        include_hoteling=bool(int_to_bool(row[8])),
        hoteling_hours_per_call=to_float(row[9]),
        port_calls=_safe_int(row[10], default=0) if row[10] is not None else None,
        include_port_ops=bool(int_to_bool(row[11])),
        port_moves_per_call=to_float(row[12]),
        cargo_teu=to_float(row[13]),
        t_per_teu_default=to_float(row[14]),
        allocation_mode=_normalize_text(row[15]),
        allocation_load_factor=to_float(row[16]),
        full_call_mode=bool(int_to_bool(row[17])),
        port_ops_scenario=_normalize_text(row[18]),
        destination_set_id=str(row[19]),
        destination_count=_safe_int(row[20]),
        success_count=_safe_int(row[21]),
        fail_count=_safe_int(row[22]),
        status=str(row[23]),
        error_message=_normalize_text(row[24]),
        duration_s=to_float(row[25]),
        started_timestamp=row[26],
        completed_timestamp=row[27],
        updated_timestamp=row[28],
    )


def _row_to_run_result_record(row: Sequence[Any]) -> BulkRunResultRecord:
    return BulkRunResultRecord(
        run_id=str(row[0]),
        scenario_key=str(row[1]),
        origin_key=str(row[2]),
        origin_name=str(row[3]),
        origin_lat=to_float(row[4]),
        origin_lon=to_float(row[5]),
        origin_uf=_normalize_text(row[6]),
        destiny_key=str(row[7]),
        destiny_name=str(row[8]),
        destiny_lat=to_float(row[9]),
        destiny_lon=to_float(row[10]),
        destiny_uf=_normalize_text(row[11]),
        input_origin=str(row[12]),
        input_destiny=str(row[13]),
        destination_set_id=str(row[14]),
        port_origin_name=_normalize_text(row[15]),
        port_destiny_name=_normalize_text(row[16]),
        status=str(row[17]),
        error_message=_normalize_text(row[18]),
        road_cost_r=to_float(row[19]),
        multimodal_cost_r=to_float(row[20]),
        cost_delta_r=to_float(row[21]),
        cost_savings_pct=to_float(row[22]),
        road_emissions_kg=to_float(row[23]),
        multimodal_emissions_kg=to_float(row[24]),
        emissions_delta_kg=to_float(row[25]),
        emissions_savings_pct=to_float(row[26]),
        road_distance_km=to_float(row[27]),
        sea_km=to_float(row[28]),
        is_approximation=bool(int_to_bool(row[29])),
        route_source=_normalize_text(row[30]),
        approximation_reference_destiny=_normalize_text(row[31]),
        approximation_reference_distance_km=to_float(row[32]),
        approximation_delta_straight_line_km=to_float(row[33]),
        approximation_notes=_normalize_text(row[34]),
        insertion_timestamp=row[35],
        updated_timestamp=row[36],
    )


def ensure_runs_table(conn: DBConnection, table_name: str = DEFAULT_RUNS_TABLE) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "bulk_runs", table):
        return
    conn.execute(_RUNS_DDL_SQL.format(table=table))
    for sql in _RUNS_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "bulk_runs", table)



def ensure_run_results_table(conn: DBConnection, table_name: str = DEFAULT_RUN_RESULTS_TABLE) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "bulk_run_results", table):
        return
    conn.execute(_RUN_RESULTS_DDL_SQL.format(table=table))
    for column_name, ddl in _RUN_RESULTS_OPTIONAL_COLUMNS:
        _ensure_column(conn, table, column_name, ddl)
    for sql in _RUN_RESULTS_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "bulk_run_results", table)



def start_run(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    origin_name: str,
    input_origin: str,
    destination_count: int,
    status: str = "running",
    table_name: str = DEFAULT_RUNS_TABLE,
) -> str:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    run_id = uuid.uuid4().hex
    conn.execute(
        f"""
        INSERT INTO {table} (
              run_id
            , origin_key
            , origin_name
            , input_origin
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
            , destination_set_id
            , destination_count
            , status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            selector.origin_key,
            origin_name,
            input_origin,
            to_float(selector.cargo_t),
            selector.truck_key,
            selector.ors_profile,
            selector.vessel_class,
            bool_to_int(selector.include_hoteling),
            to_float(selector.hoteling_hours_per_call),
            int(selector.port_calls),
            bool_to_int(selector.include_port_ops),
            to_float(selector.port_moves_per_call),
            to_float(selector.cargo_teu),
            to_float(selector.t_per_teu_default),
            selector.allocation_mode,
            to_float(selector.allocation_load_factor),
            bool_to_int(selector.full_call_mode),
            selector.port_ops_scenario,
            selector.destination_set_id,
            int(destination_count),
            status,
        ),
    )
    _log.info(
        "Started bulk run %s origin=%s cargo_t=%.3f destination_set=%s destinations=%d",
        run_id,
        origin_name,
        selector.cargo_t,
        selector.destination_set_id,
        destination_count,
    )
    return run_id


def upsert_run(
    conn: DBConnection,
    *,
    run_id: str,
    selector: BulkRunSelector,
    origin_name: str,
    input_origin: str,
    destination_count: int,
    success_count: int,
    fail_count: int,
    status: str,
    error_message: Optional[str] = None,
    duration_s: Optional[float] = None,
    started_timestamp: Any = None,
    completed_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_RUNS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    conn.execute(
        f"""
        INSERT INTO {table} (
              run_id
            , origin_key
            , origin_name
            , input_origin
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
            , destination_set_id
            , destination_count
            , success_count
            , fail_count
            , status
            , error_message
            , duration_s
            , started_timestamp
            , completed_timestamp
            , updated_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
              origin_key = excluded.origin_key
            , origin_name = excluded.origin_name
            , input_origin = excluded.input_origin
            , cargo_t = excluded.cargo_t
            , truck_key = excluded.truck_key
            , ors_profile = excluded.ors_profile
            , vessel_class = excluded.vessel_class
            , include_hoteling = excluded.include_hoteling
            , hoteling_hours_per_call = excluded.hoteling_hours_per_call
            , port_calls = excluded.port_calls
            , include_port_ops = excluded.include_port_ops
            , port_moves_per_call = excluded.port_moves_per_call
            , cargo_teu = excluded.cargo_teu
            , t_per_teu_default = excluded.t_per_teu_default
            , allocation_mode = excluded.allocation_mode
            , allocation_load_factor = excluded.allocation_load_factor
            , full_call_mode = excluded.full_call_mode
            , port_ops_scenario = excluded.port_ops_scenario
            , destination_set_id = excluded.destination_set_id
            , destination_count = excluded.destination_count
            , success_count = excluded.success_count
            , fail_count = excluded.fail_count
            , status = excluded.status
            , error_message = excluded.error_message
            , duration_s = excluded.duration_s
            , started_timestamp = COALESCE(excluded.started_timestamp, started_timestamp)
            , completed_timestamp = COALESCE(excluded.completed_timestamp, completed_timestamp)
            , updated_timestamp = COALESCE(excluded.updated_timestamp, {current_timestamp_sql()})
        """,
        (
            run_id,
            selector.origin_key,
            origin_name,
            input_origin,
            to_float(selector.cargo_t),
            selector.truck_key,
            selector.ors_profile,
            selector.vessel_class,
            bool_to_int(selector.include_hoteling),
            to_float(selector.hoteling_hours_per_call),
            int(selector.port_calls),
            bool_to_int(selector.include_port_ops),
            to_float(selector.port_moves_per_call),
            to_float(selector.cargo_teu),
            to_float(selector.t_per_teu_default),
            selector.allocation_mode,
            to_float(selector.allocation_load_factor),
            bool_to_int(selector.full_call_mode),
            selector.port_ops_scenario,
            selector.destination_set_id,
            int(destination_count),
            int(success_count),
            int(fail_count),
            status,
            error_message,
            to_float(duration_s),
            started_timestamp,
            completed_timestamp,
            updated_timestamp,
        ),
    )


def finish_run(
    conn: DBConnection,
    *,
    run_id: str,
    status: str,
    success_count: int,
    fail_count: int,
    duration_s: float,
    error_message: Optional[str] = None,
    table_name: str = DEFAULT_RUNS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    completed_sql = current_timestamp_sql() if status in {"completed", "failed"} else "completed_timestamp"
    conn.execute(
        f"""
        UPDATE {table}
           SET status = ?
             , success_count = ?
             , fail_count = ?
             , duration_s = ?
             , error_message = ?
             , completed_timestamp = {completed_sql}
             , updated_timestamp = {current_timestamp_sql()}
         WHERE run_id = ?
        """,
        (
            status,
            int(success_count),
            int(fail_count),
            to_float(duration_s),
            error_message,
            run_id,
        ),
    )
    _log.info("Finished bulk run %s status=%s success=%d fail=%d duration_s=%.2f", run_id, status, success_count, fail_count, duration_s)



def insert_run_result(
    conn: DBConnection,
    *,
    run_id: str,
    scenario_key: str,
    origin_key: str,
    origin_name: str,
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    origin_uf: Optional[str],
    destiny_key: str,
    destiny_name: str,
    destiny_lat: Optional[float],
    destiny_lon: Optional[float],
    destiny_uf: Optional[str],
    input_origin: str,
    input_destiny: str,
    destination_set_id: str,
    port_origin_name: Optional[str],
    port_destiny_name: Optional[str],
    status: str,
    error_message: Optional[str],
    road_cost_r: Optional[float],
    multimodal_cost_r: Optional[float],
    cost_delta_r: Optional[float],
    cost_savings_pct: Optional[float],
    road_emissions_kg: Optional[float],
    multimodal_emissions_kg: Optional[float],
    emissions_delta_kg: Optional[float],
    emissions_savings_pct: Optional[float],
    road_distance_km: Optional[float],
    sea_km: Optional[float],
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    ensure_run_results_table(conn, table)
    conn.execute(
        f"""
        INSERT INTO {table} (
              run_id
            , scenario_key
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
            , destination_set_id
            , port_origin_name
            , port_destiny_name
            , status
            , error_message
            , road_cost_r
            , multimodal_cost_r
            , cost_delta_r
            , cost_savings_pct
            , road_emissions_kg
            , multimodal_emissions_kg
            , emissions_delta_kg
            , emissions_savings_pct
            , road_distance_km
            , sea_km
            , is_approximation
            , route_source
            , approximation_reference_destiny
            , approximation_reference_distance_km
            , approximation_delta_straight_line_km
            , approximation_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, scenario_key) DO UPDATE SET
              origin_key = excluded.origin_key
            , origin_name = excluded.origin_name
            , origin_lat = excluded.origin_lat
            , origin_lon = excluded.origin_lon
            , origin_uf = excluded.origin_uf
            , destiny_key = excluded.destiny_key
            , destiny_name = excluded.destiny_name
            , destiny_lat = excluded.destiny_lat
            , destiny_lon = excluded.destiny_lon
            , destiny_uf = excluded.destiny_uf
            , input_origin = excluded.input_origin
            , input_destiny = excluded.input_destiny
            , destination_set_id = excluded.destination_set_id
            , port_origin_name = excluded.port_origin_name
            , port_destiny_name = excluded.port_destiny_name
            , status = excluded.status
            , error_message = excluded.error_message
            , road_cost_r = excluded.road_cost_r
            , multimodal_cost_r = excluded.multimodal_cost_r
            , cost_delta_r = excluded.cost_delta_r
            , cost_savings_pct = excluded.cost_savings_pct
            , road_emissions_kg = excluded.road_emissions_kg
            , multimodal_emissions_kg = excluded.multimodal_emissions_kg
            , emissions_delta_kg = excluded.emissions_delta_kg
            , emissions_savings_pct = excluded.emissions_savings_pct
            , road_distance_km = excluded.road_distance_km
            , sea_km = excluded.sea_km
            , is_approximation = excluded.is_approximation
            , route_source = excluded.route_source
            , approximation_reference_destiny = excluded.approximation_reference_destiny
            , approximation_reference_distance_km = excluded.approximation_reference_distance_km
            , approximation_delta_straight_line_km = excluded.approximation_delta_straight_line_km
            , approximation_notes = excluded.approximation_notes
            , updated_timestamp = {current_timestamp_sql()}
        """,
        (
            run_id,
            scenario_key,
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
            destination_set_id,
            port_origin_name,
            port_destiny_name,
            status,
            error_message,
            to_float(road_cost_r),
            to_float(multimodal_cost_r),
            to_float(cost_delta_r),
            to_float(cost_savings_pct),
            to_float(road_emissions_kg),
            to_float(multimodal_emissions_kg),
            to_float(emissions_delta_kg),
            to_float(emissions_savings_pct),
            to_float(road_distance_km),
            to_float(sea_km),
            bool_to_int(is_approximation),
            route_source,
            approximation_reference_destiny,
            to_float(approximation_reference_distance_km),
            to_float(approximation_delta_straight_line_km),
            approximation_notes,
        ),
    )


def insert_run_results(
    conn: DBConnection,
    *,
    rows: Iterable[dict[str, Any]],
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
) -> int:
    table = safe_table_name(table_name)
    ensure_run_results_table(conn, table)

    params_list: list[tuple[Any, ...]] = []
    for row in rows:
        params_list.append(
            (
                row["run_id"],
                row["scenario_key"],
                row["origin_key"],
                row["origin_name"],
                to_float(row.get("origin_lat")),
                to_float(row.get("origin_lon")),
                row.get("origin_uf"),
                row["destiny_key"],
                row["destiny_name"],
                to_float(row.get("destiny_lat")),
                to_float(row.get("destiny_lon")),
                row.get("destiny_uf"),
                row["input_origin"],
                row["input_destiny"],
                row["destination_set_id"],
                row.get("port_origin_name"),
                row.get("port_destiny_name"),
                row["status"],
                row.get("error_message"),
                to_float(row.get("road_cost_r")),
                to_float(row.get("multimodal_cost_r")),
                to_float(row.get("cost_delta_r")),
                to_float(row.get("cost_savings_pct")),
                to_float(row.get("road_emissions_kg")),
                to_float(row.get("multimodal_emissions_kg")),
                to_float(row.get("emissions_delta_kg")),
                to_float(row.get("emissions_savings_pct")),
                to_float(row.get("road_distance_km")),
                to_float(row.get("sea_km")),
                bool_to_int(bool(row.get("is_approximation"))),
                row.get("route_source"),
                row.get("approximation_reference_destiny"),
                to_float(row.get("approximation_reference_distance_km")),
                to_float(row.get("approximation_delta_straight_line_km")),
                row.get("approximation_notes"),
            )
        )

    if not params_list:
        return 0

    conn.executemany(
        f"""
        INSERT INTO {table} (
              run_id
            , scenario_key
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
            , destination_set_id
            , port_origin_name
            , port_destiny_name
            , status
            , error_message
            , road_cost_r
            , multimodal_cost_r
            , cost_delta_r
            , cost_savings_pct
            , road_emissions_kg
            , multimodal_emissions_kg
            , emissions_delta_kg
            , emissions_savings_pct
            , road_distance_km
            , sea_km
            , is_approximation
            , route_source
            , approximation_reference_destiny
            , approximation_reference_distance_km
            , approximation_delta_straight_line_km
            , approximation_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, scenario_key) DO UPDATE SET
              origin_key = excluded.origin_key
            , origin_name = excluded.origin_name
            , origin_lat = excluded.origin_lat
            , origin_lon = excluded.origin_lon
            , origin_uf = excluded.origin_uf
            , destiny_key = excluded.destiny_key
            , destiny_name = excluded.destiny_name
            , destiny_lat = excluded.destiny_lat
            , destiny_lon = excluded.destiny_lon
            , destiny_uf = excluded.destiny_uf
            , input_origin = excluded.input_origin
            , input_destiny = excluded.input_destiny
            , destination_set_id = excluded.destination_set_id
            , port_origin_name = excluded.port_origin_name
            , port_destiny_name = excluded.port_destiny_name
            , status = excluded.status
            , error_message = excluded.error_message
            , road_cost_r = excluded.road_cost_r
            , multimodal_cost_r = excluded.multimodal_cost_r
            , cost_delta_r = excluded.cost_delta_r
            , cost_savings_pct = excluded.cost_savings_pct
            , road_emissions_kg = excluded.road_emissions_kg
            , multimodal_emissions_kg = excluded.multimodal_emissions_kg
            , emissions_delta_kg = excluded.emissions_delta_kg
            , emissions_savings_pct = excluded.emissions_savings_pct
            , road_distance_km = excluded.road_distance_km
            , sea_km = excluded.sea_km
            , is_approximation = excluded.is_approximation
            , route_source = excluded.route_source
            , approximation_reference_destiny = excluded.approximation_reference_destiny
            , approximation_reference_distance_km = excluded.approximation_reference_distance_km
            , approximation_delta_straight_line_km = excluded.approximation_delta_straight_line_km
            , approximation_notes = excluded.approximation_notes
            , updated_timestamp = {current_timestamp_sql()}
        """,
        params_list,
    )
    return len(params_list)


def get_latest_completed_run(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    table_name: str = DEFAULT_RUNS_TABLE,
) -> Optional[BulkRunRecord]:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    clauses, params = _selector_clauses(selector)
    clauses.append("status = ?")
    params.append("completed")
    where = " AND ".join(clauses)
    row = conn.execute(
        f"""
        SELECT
              run_id
            , origin_key
            , origin_name
            , input_origin
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
            , destination_set_id
            , destination_count
            , success_count
            , fail_count
            , status
            , error_message
            , duration_s
            , started_timestamp
            , completed_timestamp
            , updated_timestamp
        FROM {table}
        WHERE {where}
        ORDER BY completed_timestamp DESC, updated_timestamp DESC, started_timestamp DESC
        LIMIT 1
        """,
        params,
    ).fetchone()
    if not row:
        return None
    return _row_to_run_record(row)



def list_available_origins(
    conn: DBConnection,
    *,
    destination_set_id: str,
    table_name: str = DEFAULT_RUNS_TABLE,
    limit: int = 500,
) -> List[str]:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    rows = conn.execute(
        f"""
        SELECT origin_name
        FROM (
            SELECT DISTINCT origin_name
            FROM {table}
            WHERE status = 'completed'
              AND destination_set_id = ?
              AND TRIM(COALESCE(origin_name, '')) <> ''
        ) AS distinct_origins
        ORDER BY LOWER(origin_name) ASC, origin_name ASC
        LIMIT ?
        """,
        (destination_set_id, int(limit)),
    ).fetchall()
    origins = [str(row[0]) for row in rows if row and row[0] is not None]
    _log.debug(
        "Listed bulk run origins destination_set=%s count=%d limit=%d",
        destination_set_id,
        len(origins),
        limit,
    )
    return origins



def list_available_cargo_values(
    conn: DBConnection,
    *,
    origin_key: str,
    destination_set_id: str,
    table_name: str = DEFAULT_RUNS_TABLE,
    limit: int = 100,
) -> List[float]:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table)
    rows = conn.execute(
        f"""
        SELECT DISTINCT cargo_t
        FROM {table}
        WHERE status = 'completed'
          AND origin_key = ?
          AND destination_set_id = ?
        ORDER BY cargo_t ASC
        LIMIT ?
        """,
        (origin_key, destination_set_id, int(limit)),
    ).fetchall()
    values: list[float] = []
    for row in rows:
        value = to_float(row[0])
        if value is not None:
            values.append(value)
    _log.debug(
        "Listed bulk run cargo values origin_key=%s destination_set=%s count=%d limit=%d",
        origin_key,
        destination_set_id,
        len(values),
        limit,
    )
    return values



def list_run_results(
    conn: DBConnection,
    *,
    run_id: str,
    only_success: bool = True,
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
) -> List[BulkRunResultRecord]:
    table = safe_table_name(table_name)
    ensure_run_results_table(conn, table)
    clauses = ["run_id = ?"]
    params: list[Any] = [run_id]
    if only_success:
        clauses.append("status = ?")
        params.append("ok")
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT
              run_id
            , scenario_key
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
            , destination_set_id
            , port_origin_name
            , port_destiny_name
            , status
            , error_message
            , road_cost_r
            , multimodal_cost_r
            , cost_delta_r
            , cost_savings_pct
            , road_emissions_kg
            , multimodal_emissions_kg
            , emissions_delta_kg
            , emissions_savings_pct
            , road_distance_km
            , sea_km
            , is_approximation
            , route_source
            , approximation_reference_destiny
            , approximation_reference_distance_km
            , approximation_delta_straight_line_km
            , approximation_notes
            , insertion_timestamp
            , updated_timestamp
        FROM {table}
        WHERE {where}
        ORDER BY destiny_name ASC
        """,
        params,
    ).fetchall()
    records = [_row_to_run_result_record(row) for row in rows]
    _log.debug(
        "Listed bulk run results run_id=%s only_success=%s count=%d",
        run_id,
        only_success,
        len(records),
    )
    return records
