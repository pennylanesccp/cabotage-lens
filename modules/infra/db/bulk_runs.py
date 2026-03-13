from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from typing import Any, Iterable, List, Optional, Sequence

from modules.infra.db.core import (
    DBConnection,
    current_timestamp_sql,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
    to_float,
)
from modules.infra.db.locations import (
    DEFAULT_ALIASES_TABLE,
    DEFAULT_LOCATIONS_TABLE,
    ensure_tables as ensure_location_tables,
    find_point,
    get_or_create_location,
)
from modules.infra.db.road_cache import (
    DEFAULT_TABLE as DEFAULT_ROUTE_CACHE_TABLE,
    ensure_main_table as ensure_route_cache_table,
    profile_is_hgv,
)

DEFAULT_RUNS_TABLE = "bulk_runs"
DEFAULT_RUN_RESULTS_TABLE = "bulk_run_items"

_RUNS_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      run_id                    TEXT      PRIMARY KEY
    , selector_hash             TEXT      NOT NULL
    , origin_location_id        BIGINT    NOT NULL REFERENCES {locations_table}(id)
    , origin_label              TEXT
    , input_origin              TEXT      NOT NULL
    , cargo_t                   DOUBLE PRECISION NOT NULL
    , truck_key                 TEXT      NOT NULL
    , ors_profile               TEXT      NOT NULL
    , vessel_class              TEXT
    , include_hoteling          BOOLEAN   NOT NULL DEFAULT TRUE
    , hoteling_hours_per_call   DOUBLE PRECISION
    , port_calls                INTEGER
    , include_port_ops          BOOLEAN   NOT NULL DEFAULT TRUE
    , port_moves_per_call       DOUBLE PRECISION
    , cargo_teu                 DOUBLE PRECISION
    , t_per_teu_default         DOUBLE PRECISION
    , allocation_mode           TEXT
    , allocation_load_factor    DOUBLE PRECISION
    , full_call_mode            BOOLEAN   NOT NULL DEFAULT FALSE
    , port_ops_scenario         TEXT
    , destination_set_id        TEXT      NOT NULL
    , destination_count         INTEGER   NOT NULL DEFAULT 0
    , success_count             INTEGER   NOT NULL DEFAULT 0
    , fail_count                INTEGER   NOT NULL DEFAULT 0
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , duration_s                DOUBLE PRECISION
    , started_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , completed_timestamp       TIMESTAMPTZ
    , updated_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_RUN_RESULTS_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      id                               BIGSERIAL PRIMARY KEY
    , run_id                           TEXT      NOT NULL REFERENCES {runs_table}(run_id) ON DELETE CASCADE
    , scenario_key                     TEXT      NOT NULL
    , input_destiny                    TEXT      NOT NULL
    , destination_location_id          BIGINT    REFERENCES {locations_table}(id)
    , port_origin_location_id          BIGINT    REFERENCES {locations_table}(id)
    , port_destiny_location_id         BIGINT    REFERENCES {locations_table}(id)
    , road_route_id                    BIGINT    REFERENCES {route_table}(id)
    , first_mile_route_id              BIGINT    REFERENCES {route_table}(id)
    , last_mile_route_id               BIGINT    REFERENCES {route_table}(id)
    , status                           TEXT      NOT NULL
    , error_message                    TEXT
    , road_cost_r                      DOUBLE PRECISION
    , multimodal_cost_r                DOUBLE PRECISION
    , cost_delta_r                     DOUBLE PRECISION
    , cost_savings_pct                 DOUBLE PRECISION
    , road_emissions_kg                DOUBLE PRECISION
    , multimodal_emissions_kg          DOUBLE PRECISION
    , emissions_delta_kg               DOUBLE PRECISION
    , emissions_savings_pct            DOUBLE PRECISION
    , road_distance_km                 DOUBLE PRECISION
    , sea_km                           DOUBLE PRECISION
    , is_approximation                 BOOLEAN   NOT NULL DEFAULT FALSE
    , route_source                     TEXT
    , approximation_reference_route_id BIGINT    REFERENCES {route_table}(id)
    , approximation_delta_straight_line_km DOUBLE PRECISION
    , approximation_notes              TEXT
    , insertion_timestamp              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT uq_{table}_run_scenario UNIQUE (run_id, scenario_key)
);
"""

_RUNS_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_selector_status ON {table} (selector_hash, status, updated_timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_destination_origin ON {table} (destination_set_id, status, origin_location_id);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_origin_cargo ON {table} (origin_location_id, destination_set_id, cargo_t);",
)

_RUN_RESULTS_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_run_status ON {table} (run_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_run_input_destiny ON {table} (run_id, input_destiny);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_destination_location ON {table} (destination_location_id);",
)


@dataclass(frozen=True)
class BulkRunSelector:
    origin_location_id: Optional[int]
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
    selector_hash: str
    origin_location_id: int
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
    input_destiny: str
    destination_location_id: Optional[int]
    destiny_name: str
    destiny_lat: Optional[float]
    destiny_lon: Optional[float]
    destiny_uf: Optional[str]
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
    approximation_reference_route_id: Optional[int]
    approximation_reference_destiny: Optional[str]
    approximation_reference_distance_km: Optional[float]
    approximation_delta_straight_line_km: Optional[float]
    approximation_notes: Optional[str]
    road_route_id: Optional[int]
    first_mile_route_id: Optional[int]
    last_mile_route_id: Optional[int]
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


def selector_hash(selector: BulkRunSelector) -> str:
    payload = {
        "origin_location_id": selector.origin_location_id,
        "cargo_t": round(float(selector.cargo_t), 9),
        "truck_key": str(selector.truck_key),
        "ors_profile": str(selector.ors_profile),
        "vessel_class": selector.vessel_class,
        "include_hoteling": bool(selector.include_hoteling),
        "hoteling_hours_per_call": round(float(selector.hoteling_hours_per_call), 9),
        "port_calls": int(selector.port_calls),
        "include_port_ops": bool(selector.include_port_ops),
        "port_moves_per_call": selector.port_moves_per_call,
        "cargo_teu": selector.cargo_teu,
        "t_per_teu_default": round(float(selector.t_per_teu_default), 9),
        "allocation_mode": selector.allocation_mode,
        "allocation_load_factor": round(float(selector.allocation_load_factor), 9),
        "full_call_mode": bool(selector.full_call_mode),
        "port_ops_scenario": str(selector.port_ops_scenario),
        "destination_set_id": str(selector.destination_set_id),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def ensure_runs_table(
    conn: DBConnection,
    table_name: str = DEFAULT_RUNS_TABLE,
    *,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    if schema_is_ready(conn, "bulk_runs", table):
        return
    ensure_location_tables(conn, locations_table=locations, aliases_table=DEFAULT_ALIASES_TABLE)
    conn.execute(_RUNS_DDL_SQL.format(table=table, locations_table=locations))
    for sql in _RUNS_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "bulk_runs", table)


def ensure_run_results_table(
    conn: DBConnection,
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
    *,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> None:
    table = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    if schema_is_ready(conn, "bulk_run_items", table):
        return
    ensure_runs_table(conn, runs, locations_table=locations)
    ensure_route_cache_table(conn, routes, locations_table=locations)
    conn.execute(
        _RUN_RESULTS_DDL_SQL.format(
            table=table,
            runs_table=runs,
            locations_table=locations,
            route_table=routes,
        )
    )
    for sql in _RUN_RESULTS_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "bulk_run_items", table)


def _row_to_run_record(row: Sequence[Any]) -> BulkRunRecord:
    return BulkRunRecord(
        run_id=str(row[0]),
        selector_hash=str(row[1]),
        origin_location_id=int(row[2]),
        origin_name=str(row[3]),
        input_origin=str(row[4]),
        cargo_t=float(row[5]),
        truck_key=str(row[6]),
        ors_profile=str(row[7]),
        vessel_class=_normalize_text(row[8]),
        include_hoteling=bool(row[9]),
        hoteling_hours_per_call=to_float(row[10]),
        port_calls=_safe_int(row[11], default=0) if row[11] is not None else None,
        include_port_ops=bool(row[12]),
        port_moves_per_call=to_float(row[13]),
        cargo_teu=to_float(row[14]),
        t_per_teu_default=to_float(row[15]),
        allocation_mode=_normalize_text(row[16]),
        allocation_load_factor=to_float(row[17]),
        full_call_mode=bool(row[18]),
        port_ops_scenario=_normalize_text(row[19]),
        destination_set_id=str(row[20]),
        destination_count=_safe_int(row[21]),
        success_count=_safe_int(row[22]),
        fail_count=_safe_int(row[23]),
        status=str(row[24]),
        error_message=_normalize_text(row[25]),
        duration_s=to_float(row[26]),
        started_timestamp=row[27],
        completed_timestamp=row[28],
        updated_timestamp=row[29],
    )


def _row_to_run_result_record(row: Sequence[Any]) -> BulkRunResultRecord:
    return BulkRunResultRecord(
        run_id=str(row[0]),
        scenario_key=str(row[1]),
        input_destiny=str(row[2]),
        destination_location_id=(None if row[3] is None else int(row[3])),
        destiny_name=str(row[4]),
        destiny_lat=to_float(row[5]),
        destiny_lon=to_float(row[6]),
        destiny_uf=_normalize_text(row[7]),
        port_origin_name=_normalize_text(row[8]),
        port_destiny_name=_normalize_text(row[9]),
        status=str(row[10]),
        error_message=_normalize_text(row[11]),
        road_cost_r=to_float(row[12]),
        multimodal_cost_r=to_float(row[13]),
        cost_delta_r=to_float(row[14]),
        cost_savings_pct=to_float(row[15]),
        road_emissions_kg=to_float(row[16]),
        multimodal_emissions_kg=to_float(row[17]),
        emissions_delta_kg=to_float(row[18]),
        emissions_savings_pct=to_float(row[19]),
        road_distance_km=to_float(row[20]),
        sea_km=to_float(row[21]),
        is_approximation=bool(row[22]),
        route_source=_normalize_text(row[23]),
        approximation_reference_route_id=(None if row[24] is None else int(row[24])),
        approximation_reference_destiny=_normalize_text(row[25]),
        approximation_reference_distance_km=to_float(row[26]),
        approximation_delta_straight_line_km=to_float(row[27]),
        approximation_notes=_normalize_text(row[28]),
        road_route_id=(None if row[29] is None else int(row[29])),
        first_mile_route_id=(None if row[30] is None else int(row[30])),
        last_mile_route_id=(None if row[31] is None else int(row[31])),
        insertion_timestamp=row[32],
        updated_timestamp=row[33],
    )


def _selector_for_origin(selector: BulkRunSelector, origin_location_id: int) -> BulkRunSelector:
    return replace(selector, origin_location_id=int(origin_location_id))


def _resolve_location_id(
    conn: DBConnection,
    *,
    location_id: Optional[int] = None,
    label: Any = None,
    lat: Any = None,
    lon: Any = None,
    uf: Any = None,
    provider: Any = None,
    source: str = "bulk",
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
) -> Optional[int]:
    if location_id is not None:
        return int(location_id)

    if lat is not None and lon is not None:
        label_text = _normalize_text(label) or _normalize_text(f"{lat}, {lon}") or "Point"
        location = get_or_create_location(
            conn,
            lat=lat,
            lon=lon,
            label=label_text,
            state=uf,
            provider=provider,
            table_name=locations_table,
        )
        if label_text:
            point = find_point(conn, place=label_text, table_name=aliases_table, locations_table=locations_table)
            if point is None:
                from modules.infra.db.locations import upsert_alias

                upsert_alias(
                    conn,
                    place=label_text,
                    location_id=location["location_id"],
                    alias_label=label_text,
                    provider=provider,
                    source=source,
                    table_name=aliases_table,
                    locations_table=locations_table,
                )
        return int(location["location_id"])

    label_text = _normalize_text(label)
    if not label_text:
        return None
    point = find_point(conn, place=label_text, table_name=aliases_table, locations_table=locations_table)
    if point is None:
        return None
    return int(point["location_id"])


def _resolve_route_id(
    conn: DBConnection,
    *,
    origin_location_id: Optional[int],
    destiny_location_id: Optional[int],
    is_hgv: bool,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[int]:
    if origin_location_id is None or destiny_location_id is None:
        return None
    table = safe_table_name(route_table)
    ensure_route_cache_table(conn, table, locations_table=locations_table)
    row = conn.execute(
        f"""
        SELECT id
        FROM {table}
        WHERE origin_location_id = ?
          AND destiny_location_id = ?
          AND is_hgv = ?
        LIMIT 1
        """,
        (int(origin_location_id), int(destiny_location_id), bool(is_hgv)),
    ).fetchone()
    if not row:
        return None
    return int(row[0])


def _run_origin_location_id(
    conn: DBConnection,
    *,
    run_id: str,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[int]:
    table = safe_table_name(runs_table)
    ensure_runs_table(conn, table, locations_table=locations_table)
    row = conn.execute(
        f"""
        SELECT origin_location_id
        FROM {table}
        WHERE run_id = ?
        LIMIT 1
        """,
        (str(run_id),),
    ).fetchone()
    if not row or row[0] is None:
        return None
    return int(row[0])


def _origin_label_for_run(
    conn: DBConnection,
    *,
    origin_location_id: int,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> str:
    locations = safe_table_name(locations_table)
    ensure_location_tables(conn, locations_table=locations, aliases_table=DEFAULT_ALIASES_TABLE)
    row = conn.execute(
        f"""
        SELECT COALESCE(NULLIF(TRIM(label), ''), lat6::text || ', ' || lon6::text)
        FROM {locations}
        WHERE id = ?
        LIMIT 1
        """,
        (int(origin_location_id),),
    ).fetchone()
    return str(row[0]) if row and row[0] not in (None, "") else str(origin_location_id)


def upsert_run(
    conn: DBConnection,
    *,
    run_id: str,
    selector: BulkRunSelector,
    origin_name: str,
    input_origin: str,
    destination_count: int = 0,
    success_count: int = 0,
    fail_count: int = 0,
    status: str = "running",
    error_message: Optional[str] = None,
    duration_s: Optional[float] = None,
    started_timestamp: Any = None,
    completed_timestamp: Any = None,
    updated_timestamp: Any = None,
    origin_location_id: Optional[int] = None,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> str:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table, locations_table=locations_table)

    resolved_origin_id = int(origin_location_id or selector.origin_location_id or 0)
    if resolved_origin_id <= 0:
        resolved_origin_id = _resolve_location_id(
            conn,
            label=origin_name or input_origin,
            locations_table=locations_table,
        ) or 0
    if resolved_origin_id <= 0:
        raise RuntimeError("Bulk runs require a canonical origin_location_id.")

    normalized_selector = _selector_for_origin(selector, resolved_origin_id)
    row = conn.execute(
        f"""
        INSERT INTO {table} (
              run_id
            , selector_hash
            , origin_location_id
            , origin_label
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
        ) VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
              COALESCE(?, {current_timestamp_sql()}),
              ?,
              COALESCE(?, {current_timestamp_sql()})
        )
        ON CONFLICT(run_id) DO UPDATE SET
              selector_hash = excluded.selector_hash
            , origin_location_id = excluded.origin_location_id
            , origin_label = excluded.origin_label
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
            , started_timestamp = COALESCE(excluded.started_timestamp, {table}.started_timestamp)
            , completed_timestamp = excluded.completed_timestamp
            , updated_timestamp = COALESCE(excluded.updated_timestamp, {current_timestamp_sql()})
        RETURNING run_id
        """,
        (
            str(run_id),
            selector_hash(normalized_selector),
            resolved_origin_id,
            _normalize_text(origin_name) or _origin_label_for_run(
                conn,
                origin_location_id=resolved_origin_id,
                locations_table=locations_table,
            ),
            str(input_origin),
            float(normalized_selector.cargo_t),
            str(normalized_selector.truck_key),
            str(normalized_selector.ors_profile),
            normalized_selector.vessel_class,
            bool(normalized_selector.include_hoteling),
            float(normalized_selector.hoteling_hours_per_call),
            int(normalized_selector.port_calls),
            bool(normalized_selector.include_port_ops),
            to_float(normalized_selector.port_moves_per_call),
            to_float(normalized_selector.cargo_teu),
            float(normalized_selector.t_per_teu_default),
            normalized_selector.allocation_mode,
            float(normalized_selector.allocation_load_factor),
            bool(normalized_selector.full_call_mode),
            str(normalized_selector.port_ops_scenario),
            str(normalized_selector.destination_set_id),
            int(destination_count),
            int(success_count),
            int(fail_count),
            str(status),
            error_message,
            to_float(duration_s),
            started_timestamp,
            completed_timestamp,
            updated_timestamp,
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def start_run(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    origin_name: str,
    input_origin: str,
    destination_count: int,
    run_id: Optional[str] = None,
    origin_location_id: Optional[int] = None,
    started_timestamp: Any = None,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> str:
    generated = str(run_id or uuid.uuid4().hex)
    return upsert_run(
        conn,
        run_id=generated,
        selector=selector,
        origin_name=origin_name,
        input_origin=input_origin,
        destination_count=destination_count,
        success_count=0,
        fail_count=0,
        status="running",
        error_message=None,
        duration_s=None,
        started_timestamp=started_timestamp,
        completed_timestamp=None,
        updated_timestamp=started_timestamp,
        origin_location_id=origin_location_id,
        table_name=table_name,
        locations_table=locations_table,
    )


def finish_run(
    conn: DBConnection,
    *,
    run_id: str,
    status: str,
    success_count: int,
    fail_count: int,
    duration_s: Optional[float],
    error_message: Optional[str] = None,
    completed_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table, locations_table=locations_table)
    conn.execute(
        f"""
        UPDATE {table}
           SET status = ?
             , success_count = ?
             , fail_count = ?
             , duration_s = ?
             , error_message = ?
             , completed_timestamp = COALESCE(?, {current_timestamp_sql()})
             , updated_timestamp = COALESCE(?, {current_timestamp_sql()})
         WHERE run_id = ?
        """,
        (
            str(status),
            int(success_count),
            int(fail_count),
            to_float(duration_s),
            error_message,
            completed_timestamp,
            updated_timestamp,
            str(run_id),
        ),
    )


def get_latest_completed_run(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[BulkRunRecord]:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table, locations_table=locations_table)
    row = conn.execute(
        f"""
        SELECT
              run_id
            , selector_hash
            , origin_location_id
            , COALESCE(NULLIF(TRIM(origin_label), ''), origin_location_id::text)
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
        WHERE selector_hash = ?
          AND status = 'completed'
        ORDER BY completed_timestamp DESC NULLS LAST, updated_timestamp DESC, started_timestamp DESC
        LIMIT 1
        """,
        (selector_hash(selector),),
    ).fetchone()
    if not row:
        return None
    return _row_to_run_record(row)


def list_available_origins(
    conn: DBConnection,
    *,
    destination_set_id: str,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    limit: int = 2_000,
) -> List[str]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_runs_table(conn, table, locations_table=locations)
    rows = conn.execute(
        f"""
        SELECT DISTINCT
            COALESCE(NULLIF(TRIM(r.origin_label), ''), NULLIF(TRIM(l.label), ''), l.lat6::text || ', ' || l.lon6::text)
        FROM {table} AS r
        INNER JOIN {locations} AS l
                ON l.id = r.origin_location_id
        WHERE r.destination_set_id = ?
        ORDER BY 1 ASC
        LIMIT ?
        """,
        (str(destination_set_id), int(limit)),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] not in (None, "")]


def list_available_cargo_values(
    conn: DBConnection,
    *,
    origin_location_id: int,
    destination_set_id: str,
    table_name: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    limit: int = 100,
) -> List[float]:
    table = safe_table_name(table_name)
    ensure_runs_table(conn, table, locations_table=locations_table)
    rows = conn.execute(
        f"""
        SELECT DISTINCT cargo_t
        FROM {table}
        WHERE origin_location_id = ?
          AND destination_set_id = ?
        ORDER BY cargo_t ASC
        LIMIT ?
        """,
        (int(origin_location_id), str(destination_set_id), int(limit)),
    ).fetchall()
    return [float(row[0]) for row in rows if row and row[0] is not None]


def _result_projection_sql(items_table: str, runs_table: str, locations_table: str, route_table: str) -> str:
    routes = safe_table_name(route_table)
    return f"""
    SELECT
          i.run_id
        , i.scenario_key
        , i.input_destiny
        , i.destination_location_id
        , COALESCE(NULLIF(TRIM(dest.label), ''), i.input_destiny)
        , dest.lat6
        , dest.lon6
        , dest.state
        , COALESCE(NULLIF(TRIM(port_origin.label), ''), NULL)
        , COALESCE(NULLIF(TRIM(port_dest.label), ''), NULL)
        , i.status
        , i.error_message
        , i.road_cost_r
        , i.multimodal_cost_r
        , i.cost_delta_r
        , i.cost_savings_pct
        , i.road_emissions_kg
        , i.multimodal_emissions_kg
        , i.emissions_delta_kg
        , i.emissions_savings_pct
        , i.road_distance_km
        , i.sea_km
        , i.is_approximation
        , i.route_source
        , i.approximation_reference_route_id
        , COALESCE(NULLIF(TRIM(approx_dest.label), ''), NULL)
        , approx_route.distance_km
        , i.approximation_delta_straight_line_km
        , i.approximation_notes
        , i.road_route_id
        , i.first_mile_route_id
        , i.last_mile_route_id
        , i.insertion_timestamp
        , i.updated_timestamp
    FROM {items_table} AS i
    INNER JOIN {runs_table} AS r
            ON r.run_id = i.run_id
    LEFT JOIN {locations_table} AS dest
           ON dest.id = i.destination_location_id
    LEFT JOIN {locations_table} AS port_origin
           ON port_origin.id = i.port_origin_location_id
    LEFT JOIN {locations_table} AS port_dest
           ON port_dest.id = i.port_destiny_location_id
    LEFT JOIN {routes} AS approx_route
           ON approx_route.id = i.approximation_reference_route_id
    LEFT JOIN {locations_table} AS approx_dest
           ON approx_dest.id = approx_route.destiny_location_id
    """


def list_run_results(
    conn: DBConnection,
    *,
    run_id: str,
    only_success: Optional[bool] = None,
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> List[BulkRunResultRecord]:
    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_run_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    clauses = ["i.run_id = ?"]
    params: list[Any] = [str(run_id)]
    if only_success is True:
        clauses.append("i.status = 'ok'")
    elif only_success is False:
        clauses.append("i.status <> 'ok'")

    rows = conn.execute(
        _result_projection_sql(items, runs, locations, routes)
        + f"""
        WHERE {' AND '.join(clauses)}
        ORDER BY i.input_destiny ASC, i.updated_timestamp DESC, i.id DESC
        """,
        params,
    ).fetchall()
    return [_row_to_run_result_record(row) for row in rows]


def insert_run_result(
    conn: DBConnection,
    *,
    run_id: str,
    scenario_key: str,
    input_destiny: str,
    destination_location_id: Optional[int] = None,
    destiny_name: Optional[str] = None,
    destiny_lat: Optional[float] = None,
    destiny_lon: Optional[float] = None,
    destiny_uf: Optional[str] = None,
    port_origin_location_id: Optional[int] = None,
    port_origin_name: Optional[str] = None,
    port_origin_lat: Optional[float] = None,
    port_origin_lon: Optional[float] = None,
    port_destiny_location_id: Optional[int] = None,
    port_destiny_name: Optional[str] = None,
    port_destiny_lat: Optional[float] = None,
    port_destiny_lon: Optional[float] = None,
    road_route_id: Optional[int] = None,
    first_mile_route_id: Optional[int] = None,
    last_mile_route_id: Optional[int] = None,
    status: str = "ok",
    error_message: Optional[str] = None,
    road_cost_r: Optional[float] = None,
    multimodal_cost_r: Optional[float] = None,
    cost_delta_r: Optional[float] = None,
    cost_savings_pct: Optional[float] = None,
    road_emissions_kg: Optional[float] = None,
    multimodal_emissions_kg: Optional[float] = None,
    emissions_delta_kg: Optional[float] = None,
    emissions_savings_pct: Optional[float] = None,
    road_distance_km: Optional[float] = None,
    sea_km: Optional[float] = None,
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    approximation_reference_route_id: Optional[int] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_distance_km: Optional[float] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
    ors_profile: str = "driving-hgv",
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    **_ignored: Any,
) -> None:
    del approximation_distance_km
    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_run_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    resolved_destination_id = _resolve_location_id(
        conn,
        location_id=destination_location_id,
        label=destiny_name or input_destiny,
        lat=destiny_lat,
        lon=destiny_lon,
        uf=destiny_uf,
        source="bulk_result",
        locations_table=locations,
        aliases_table=aliases_table,
    )
    resolved_port_origin_id = _resolve_location_id(
        conn,
        location_id=port_origin_location_id,
        label=port_origin_name,
        lat=port_origin_lat,
        lon=port_origin_lon,
        source="port_origin",
        locations_table=locations,
        aliases_table=aliases_table,
    )
    resolved_port_destiny_id = _resolve_location_id(
        conn,
        location_id=port_destiny_location_id,
        label=port_destiny_name,
        lat=port_destiny_lat,
        lon=port_destiny_lon,
        source="port_destiny",
        locations_table=locations,
        aliases_table=aliases_table,
    )

    origin_location_id = _run_origin_location_id(
        conn,
        run_id=run_id,
        runs_table=runs,
        locations_table=locations,
    )
    route_is_hgv = profile_is_hgv(ors_profile)

    resolved_road_route_id = road_route_id or _resolve_route_id(
        conn,
        origin_location_id=origin_location_id,
        destiny_location_id=resolved_destination_id,
        is_hgv=route_is_hgv,
        route_table=routes,
        locations_table=locations,
    )
    resolved_first_mile_route_id = first_mile_route_id or _resolve_route_id(
        conn,
        origin_location_id=origin_location_id,
        destiny_location_id=resolved_port_origin_id,
        is_hgv=route_is_hgv,
        route_table=routes,
        locations_table=locations,
    )
    resolved_last_mile_route_id = last_mile_route_id or _resolve_route_id(
        conn,
        origin_location_id=resolved_port_destiny_id,
        destiny_location_id=resolved_destination_id,
        is_hgv=route_is_hgv,
        route_table=routes,
        locations_table=locations,
    )
    resolved_approx_route_id = approximation_reference_route_id
    if resolved_approx_route_id is None and approximation_reference_destiny:
        approx_destiny_id = _resolve_location_id(
            conn,
            label=approximation_reference_destiny,
            source="bulk_approx_reference",
            locations_table=locations,
            aliases_table=aliases_table,
        )
        resolved_approx_route_id = _resolve_route_id(
            conn,
            origin_location_id=origin_location_id,
            destiny_location_id=approx_destiny_id,
            is_hgv=route_is_hgv,
            route_table=routes,
            locations_table=locations,
        )

    conn.execute(
        f"""
        INSERT INTO {items} (
              run_id
            , scenario_key
            , input_destiny
            , destination_location_id
            , port_origin_location_id
            , port_destiny_location_id
            , road_route_id
            , first_mile_route_id
            , last_mile_route_id
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
            , approximation_reference_route_id
            , approximation_delta_straight_line_km
            , approximation_notes
            , insertion_timestamp
            , updated_timestamp
        ) VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
              COALESCE(?, {current_timestamp_sql()}),
              COALESCE(?, {current_timestamp_sql()})
        )
        ON CONFLICT(run_id, scenario_key) DO UPDATE SET
              input_destiny = excluded.input_destiny
            , destination_location_id = excluded.destination_location_id
            , port_origin_location_id = excluded.port_origin_location_id
            , port_destiny_location_id = excluded.port_destiny_location_id
            , road_route_id = excluded.road_route_id
            , first_mile_route_id = excluded.first_mile_route_id
            , last_mile_route_id = excluded.last_mile_route_id
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
            , approximation_reference_route_id = excluded.approximation_reference_route_id
            , approximation_delta_straight_line_km = excluded.approximation_delta_straight_line_km
            , approximation_notes = excluded.approximation_notes
            , updated_timestamp = COALESCE(excluded.updated_timestamp, {current_timestamp_sql()})
        """,
        (
            str(run_id),
            str(scenario_key),
            str(input_destiny),
            resolved_destination_id,
            resolved_port_origin_id,
            resolved_port_destiny_id,
            resolved_road_route_id,
            resolved_first_mile_route_id,
            resolved_last_mile_route_id,
            str(status),
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
            bool(is_approximation),
            route_source,
            resolved_approx_route_id,
            to_float(approximation_delta_straight_line_km),
            approximation_notes,
            insertion_timestamp,
            updated_timestamp,
        ),
    )


def insert_run_results(
    conn: DBConnection,
    *,
    rows: Iterable[dict[str, Any]],
    table_name: str = DEFAULT_RUN_RESULTS_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> int:
    count = 0
    for row in rows:
        insert_run_result(
            conn,
            table_name=table_name,
            runs_table=runs_table,
            locations_table=locations_table,
            route_table=route_table,
            **row,
        )
        count += 1
    return count
