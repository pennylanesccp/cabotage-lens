from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence

from modules.infra.db.bulk_runs import (
    DEFAULT_RUNS_TABLE,
    DEFAULT_RUN_RESULTS_TABLE,
    BulkRunSelector,
    ensure_run_results_table,
    insert_run_result,
    insert_run_results,
    selector_hash,
)
from modules.infra.db.core import DBConnection, safe_table_name, to_float
from modules.infra.db.locations import DEFAULT_LOCATIONS_TABLE
from modules.infra.db.road_cache import DEFAULT_TABLE as DEFAULT_ROUTE_CACHE_TABLE

DEFAULT_TABLE = DEFAULT_RUN_RESULTS_TABLE


@dataclass(frozen=True)
class BulkResultRecord:
    scenario_key: str
    run_id: str
    destination_set_id: str
    origin_location_id: int
    origin_name: str
    input_origin: str
    destination_location_id: Optional[int]
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
    port_origin_name: Optional[str]
    port_destiny_name: Optional[str]
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


def ensure_results_table(
    conn: DBConnection,
    table_name: str = DEFAULT_TABLE,
    *,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> None:
    ensure_run_results_table(
        conn,
        table_name,
        runs_table=runs_table,
        locations_table=locations_table,
        route_table=route_table,
    )


def _latest_results_cte(items_table: str, runs_table: str, locations_table: str, route_table: str) -> str:
    return f"""
    WITH matching_runs AS (
        SELECT
              r.run_id
            , r.origin_location_id
            , COALESCE(NULLIF(TRIM(r.origin_label), ''), NULLIF(TRIM(origin_loc.label), ''), r.origin_location_id::text) AS origin_name
            , r.input_origin
            , r.cargo_t
            , r.truck_key
            , r.ors_profile
            , r.vessel_class
            , r.include_hoteling
            , r.hoteling_hours_per_call
            , r.port_calls
            , r.include_port_ops
            , r.port_moves_per_call
            , r.cargo_teu
            , r.t_per_teu_default
            , r.allocation_mode
            , r.allocation_load_factor
            , r.full_call_mode
            , r.port_ops_scenario
            , r.destination_set_id
            , COALESCE(r.completed_timestamp, r.updated_timestamp, r.started_timestamp) AS run_sort_timestamp
        FROM {runs_table} AS r
        LEFT JOIN {locations_table} AS origin_loc
               ON origin_loc.id = r.origin_location_id
        WHERE r.selector_hash = ?
    ),
    ranked AS (
        SELECT
              i.scenario_key
            , i.run_id
            , r.destination_set_id
            , r.origin_location_id
            , r.origin_name
            , r.input_origin
            , i.destination_location_id
            , COALESCE(NULLIF(TRIM(dest.label), ''), i.input_destiny) AS destiny_name
            , i.input_destiny
            , r.cargo_t
            , r.truck_key
            , r.ors_profile
            , r.vessel_class
            , r.include_hoteling
            , r.hoteling_hours_per_call
            , r.port_calls
            , r.include_port_ops
            , r.port_moves_per_call
            , r.cargo_teu
            , r.t_per_teu_default
            , r.allocation_mode
            , r.allocation_load_factor
            , r.full_call_mode
            , r.port_ops_scenario
            , i.status
            , i.error_message
            , dest.lat6
            , dest.lon6
            , dest.state
            , port_origin.label AS port_origin_name
            , port_dest.label AS port_destiny_name
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
            , approx_dest.label AS approximation_reference_destiny
            , approx_route.distance_km AS approximation_reference_distance_km
            , i.approximation_delta_straight_line_km
            , i.approximation_notes
            , i.updated_timestamp
            , ROW_NUMBER() OVER (
                  PARTITION BY LOWER(TRIM(i.input_destiny))
                  ORDER BY r.run_sort_timestamp DESC NULLS LAST, i.updated_timestamp DESC, i.insertion_timestamp DESC, i.id DESC
              ) AS row_rank
        FROM {items_table} AS i
        INNER JOIN matching_runs AS r
                ON r.run_id = i.run_id
        LEFT JOIN {locations_table} AS dest
               ON dest.id = i.destination_location_id
        LEFT JOIN {locations_table} AS port_origin
               ON port_origin.id = i.port_origin_location_id
        LEFT JOIN {locations_table} AS port_dest
               ON port_dest.id = i.port_destiny_location_id
        LEFT JOIN {route_table} AS approx_route
               ON approx_route.id = i.approximation_reference_route_id
        LEFT JOIN {locations_table} AS approx_dest
               ON approx_dest.id = approx_route.destiny_location_id
    )
    """


def _selector_filters_sql(*, include_destination_set: bool) -> str:
    clauses = [
        "r.origin_location_id = ?",
        "r.cargo_t = ?",
        "r.truck_key = ?",
        "r.ors_profile = ?",
        "r.vessel_class IS NOT DISTINCT FROM ?",
        "r.include_hoteling = ?",
        "r.hoteling_hours_per_call = ?",
        "r.port_calls = ?",
        "r.include_port_ops = ?",
        "r.port_moves_per_call IS NOT DISTINCT FROM ?",
        "r.cargo_teu IS NOT DISTINCT FROM ?",
        "r.t_per_teu_default = ?",
        "r.allocation_mode IS NOT DISTINCT FROM ?",
        "r.allocation_load_factor = ?",
        "r.full_call_mode = ?",
        "r.port_ops_scenario = ?",
    ]
    if include_destination_set:
        clauses.append("r.destination_set_id = ?")
    return "\n          AND ".join(clauses)


def _selector_filter_params(selector: BulkRunSelector, *, include_destination_set: bool) -> list[Any]:
    params: list[Any] = [
        int(selector.origin_location_id or 0),
        float(selector.cargo_t),
        str(selector.truck_key),
        str(selector.ors_profile),
        selector.vessel_class,
        bool(selector.include_hoteling),
        float(selector.hoteling_hours_per_call),
        int(selector.port_calls),
        bool(selector.include_port_ops),
        to_float(selector.port_moves_per_call),
        to_float(selector.cargo_teu),
        float(selector.t_per_teu_default),
        selector.allocation_mode,
        float(selector.allocation_load_factor),
        bool(selector.full_call_mode),
        str(selector.port_ops_scenario),
    ]
    if include_destination_set:
        params.append(str(selector.destination_set_id))
    return params


def _latest_results_for_selector_cte(
    items_table: str,
    runs_table: str,
    locations_table: str,
    route_table: str,
    *,
    include_destination_set: bool,
) -> str:
    return f"""
    WITH matching_runs AS (
        SELECT
              r.run_id
            , r.origin_location_id
            , COALESCE(NULLIF(TRIM(r.origin_label), ''), NULLIF(TRIM(origin_loc.label), ''), r.origin_location_id::text) AS origin_name
            , r.input_origin
            , r.cargo_t
            , r.truck_key
            , r.ors_profile
            , r.vessel_class
            , r.include_hoteling
            , r.hoteling_hours_per_call
            , r.port_calls
            , r.include_port_ops
            , r.port_moves_per_call
            , r.cargo_teu
            , r.t_per_teu_default
            , r.allocation_mode
            , r.allocation_load_factor
            , r.full_call_mode
            , r.port_ops_scenario
            , r.destination_set_id
            , COALESCE(r.completed_timestamp, r.updated_timestamp, r.started_timestamp) AS run_sort_timestamp
        FROM {runs_table} AS r
        LEFT JOIN {locations_table} AS origin_loc
               ON origin_loc.id = r.origin_location_id
        WHERE {_selector_filters_sql(include_destination_set=include_destination_set)}
    ),
    ranked AS (
        SELECT
              i.scenario_key
            , i.run_id
            , r.destination_set_id
            , r.origin_location_id
            , r.origin_name
            , r.input_origin
            , i.destination_location_id
            , COALESCE(NULLIF(TRIM(dest.label), ''), i.input_destiny) AS destiny_name
            , i.input_destiny
            , r.cargo_t
            , r.truck_key
            , r.ors_profile
            , r.vessel_class
            , r.include_hoteling
            , r.hoteling_hours_per_call
            , r.port_calls
            , r.include_port_ops
            , r.port_moves_per_call
            , r.cargo_teu
            , r.t_per_teu_default
            , r.allocation_mode
            , r.allocation_load_factor
            , r.full_call_mode
            , r.port_ops_scenario
            , i.status
            , i.error_message
            , dest.lat6
            , dest.lon6
            , dest.state
            , port_origin.label AS port_origin_name
            , port_dest.label AS port_destiny_name
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
            , approx_dest.label AS approximation_reference_destiny
            , approx_route.distance_km AS approximation_reference_distance_km
            , i.approximation_delta_straight_line_km
            , i.approximation_notes
            , i.updated_timestamp
            , ROW_NUMBER() OVER (
                  PARTITION BY LOWER(TRIM(i.input_destiny))
                  ORDER BY r.run_sort_timestamp DESC NULLS LAST, i.updated_timestamp DESC, i.insertion_timestamp DESC, i.id DESC
              ) AS row_rank
        FROM {items_table} AS i
        INNER JOIN matching_runs AS r
                ON r.run_id = i.run_id
        LEFT JOIN {locations_table} AS dest
               ON dest.id = i.destination_location_id
        LEFT JOIN {locations_table} AS port_origin
               ON port_origin.id = i.port_origin_location_id
        LEFT JOIN {locations_table} AS port_dest
               ON port_dest.id = i.port_destiny_location_id
        LEFT JOIN {route_table} AS approx_route
               ON approx_route.id = i.approximation_reference_route_id
        LEFT JOIN {locations_table} AS approx_dest
               ON approx_dest.id = approx_route.destiny_location_id
    )
    """


def _row_to_record(row: Sequence[Any]) -> BulkResultRecord:
    return BulkResultRecord(
        scenario_key=str(row[0]),
        run_id=str(row[1]),
        destination_set_id=str(row[2]),
        origin_location_id=int(row[3]),
        origin_name=str(row[4]),
        input_origin=str(row[5]),
        destination_location_id=(None if row[6] is None else int(row[6])),
        destiny_name=str(row[7]),
        input_destiny=str(row[8]),
        cargo_t=float(row[9]),
        truck_key=str(row[10]),
        ors_profile=str(row[11]),
        vessel_class=_normalize_text(row[12]),
        include_hoteling=bool(row[13]),
        hoteling_hours_per_call=to_float(row[14]),
        port_calls=_safe_int(row[15], default=0) if row[15] is not None else None,
        include_port_ops=bool(row[16]),
        port_moves_per_call=to_float(row[17]),
        cargo_teu=to_float(row[18]),
        t_per_teu_default=to_float(row[19]),
        allocation_mode=_normalize_text(row[20]),
        allocation_load_factor=to_float(row[21]),
        full_call_mode=bool(row[22]),
        port_ops_scenario=_normalize_text(row[23]),
        status=str(row[24]),
        error_message=_normalize_text(row[25]),
        destiny_lat=to_float(row[26]),
        destiny_lon=to_float(row[27]),
        destiny_uf=_normalize_text(row[28]),
        port_origin_name=_normalize_text(row[29]),
        port_destiny_name=_normalize_text(row[30]),
        road_cost_r=to_float(row[31]),
        multimodal_cost_r=to_float(row[32]),
        cost_delta_r=to_float(row[33]),
        cost_savings_pct=to_float(row[34]),
        road_emissions_kg=to_float(row[35]),
        multimodal_emissions_kg=to_float(row[36]),
        emissions_delta_kg=to_float(row[37]),
        emissions_savings_pct=to_float(row[38]),
        road_distance_km=to_float(row[39]),
        sea_km=to_float(row[40]),
        is_approximation=bool(row[41]),
        route_source=_normalize_text(row[42]),
        approximation_reference_destiny=_normalize_text(row[43]),
        approximation_reference_distance_km=to_float(row[44]),
        approximation_delta_straight_line_km=to_float(row[45]),
        approximation_notes=_normalize_text(row[46]),
        updated_timestamp=row[47],
    )


def summarize_results(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> BulkResultSummary:
    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    row = conn.execute(
        _latest_results_cte(items, runs, locations, routes)
        + """
        SELECT
              COUNT(*) AS row_count
            , SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS success_count
            , SUM(CASE WHEN status <> 'ok' THEN 1 ELSE 0 END) AS fail_count
            , MAX(updated_timestamp) AS latest_updated_timestamp
            , (
                SELECT run_id
                FROM ranked
                WHERE row_rank = 1
                ORDER BY updated_timestamp DESC, run_id DESC
                LIMIT 1
              ) AS latest_run_id
        FROM ranked
        WHERE row_rank = 1
        """,
        (selector_hash(selector),),
    ).fetchone()
    if not row:
        return BulkResultSummary(0, 0, 0, None, None)
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
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> List[BulkResultRecord]:
    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    clauses = ["row_rank = 1"]
    if only_success is True:
        clauses.append("status = 'ok'")
    elif only_success is False:
        clauses.append("status <> 'ok'")

    rows = conn.execute(
        _latest_results_cte(items, runs, locations, routes)
        + f"""
        SELECT
              scenario_key
            , run_id
            , destination_set_id
            , origin_location_id
            , origin_name
            , input_origin
            , destination_location_id
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
            , lat6
            , lon6
            , state
            , port_origin_name
            , port_destiny_name
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
            , updated_timestamp
        FROM ranked
        WHERE {' AND '.join(clauses)}
        ORDER BY destiny_name ASC, updated_timestamp DESC
        """,
        (selector_hash(selector),),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_results_for_origin_scenario(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    only_success: Optional[bool] = None,
    include_all_destination_sets: bool = False,
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> List[BulkResultRecord]:
    if selector.origin_location_id is None:
        return []

    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    clauses = ["row_rank = 1"]
    if only_success is True:
        clauses.append("status = 'ok'")
    elif only_success is False:
        clauses.append("status <> 'ok'")

    rows = conn.execute(
        _latest_results_for_selector_cte(
            items,
            runs,
            locations,
            routes,
            include_destination_set=(not include_all_destination_sets),
        )
        + f"""
        SELECT
              scenario_key
            , run_id
            , destination_set_id
            , origin_location_id
            , origin_name
            , input_origin
            , destination_location_id
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
            , lat6
            , lon6
            , state
            , port_origin_name
            , port_destiny_name
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
            , updated_timestamp
        FROM ranked
        WHERE {' AND '.join(clauses)}
        ORDER BY destiny_name ASC, updated_timestamp DESC
        """,
        _selector_filter_params(
            selector,
            include_destination_set=(not include_all_destination_sets),
        ),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_input_destiny_keys(
    conn: DBConnection,
    *,
    selector: BulkRunSelector,
    only_success: Optional[bool] = None,
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> List[str]:
    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    clauses = ["TRIM(COALESCE(i.input_destiny, '')) <> ''"]
    if only_success is True:
        clauses.append("i.status = 'ok'")
    elif only_success is False:
        clauses.append("i.status <> 'ok'")

    rows = conn.execute(
        f"""
        SELECT DISTINCT LOWER(TRIM(i.input_destiny)) AS input_destiny_key
        FROM {items} AS i
        INNER JOIN {runs} AS r
                ON r.run_id = i.run_id
        WHERE r.selector_hash = ?
          AND {' AND '.join(clauses)}
        ORDER BY input_destiny_key ASC
        """,
        (selector_hash(selector),),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] not in (None, "")]


def list_latest_successful_points_by_input_keys(
    conn: DBConnection,
    *,
    input_keys: Iterable[str],
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> dict[str, dict[str, Any]]:
    normalized_keys = sorted(
        {
            str(value).strip().lower()
            for value in input_keys
            if str(value).strip()
        }
    )
    if not normalized_keys:
        return {}

    items = safe_table_name(table_name)
    runs = safe_table_name(runs_table)
    locations = safe_table_name(locations_table)
    routes = safe_table_name(route_table)
    ensure_results_table(
        conn,
        items,
        runs_table=runs,
        locations_table=locations,
        route_table=routes,
    )

    placeholders = ", ".join(["?"] * len(normalized_keys))
    rows = conn.execute(
        f"""
        WITH ranked AS (
            SELECT
                  LOWER(TRIM(i.input_destiny)) AS input_destiny_key
                , i.destination_location_id
                , COALESCE(NULLIF(TRIM(dest.label), ''), i.input_destiny) AS destiny_name
                , dest.lat6
                , dest.lon6
                , dest.state
                , ROW_NUMBER() OVER (
                      PARTITION BY LOWER(TRIM(i.input_destiny))
                      ORDER BY COALESCE(r.completed_timestamp, r.updated_timestamp, r.started_timestamp, i.updated_timestamp, i.insertion_timestamp) DESC NULLS LAST,
                               i.updated_timestamp DESC,
                               i.insertion_timestamp DESC,
                               i.id DESC
                  ) AS row_rank
            FROM {items} AS i
            INNER JOIN {runs} AS r
                    ON r.run_id = i.run_id
            LEFT JOIN {locations} AS dest
                   ON dest.id = i.destination_location_id
            WHERE i.status = 'ok'
              AND TRIM(COALESCE(i.input_destiny, '')) <> ''
              AND LOWER(TRIM(i.input_destiny)) IN ({placeholders})
              AND dest.lat6 IS NOT NULL
              AND dest.lon6 IS NOT NULL
        )
        SELECT
              input_destiny_key
            , destination_location_id
            , destiny_name
            , lat6
            , lon6
            , state
        FROM ranked
        WHERE row_rank = 1
        """,
        normalized_keys,
    ).fetchall()
    return {
        str(row[0]): {
            "location_id": (None if row[1] is None else int(row[1])),
            "label": str(row[2]),
            "lat": float(row[3]),
            "lon": float(row[4]),
            "uf": _normalize_text(row[5]),
        }
        for row in rows
        if row and row[0] not in (None, "") and row[3] is not None and row[4] is not None
    }


def upsert_result(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
    **values: Any,
) -> None:
    insert_run_result(
        conn,
        table_name=table_name,
        runs_table=runs_table,
        locations_table=locations_table,
        route_table=route_table,
        **values,
    )


def upsert_results(
    conn: DBConnection,
    *,
    rows: Iterable[dict[str, Any]],
    table_name: str = DEFAULT_TABLE,
    runs_table: str = DEFAULT_RUNS_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    route_table: str = DEFAULT_ROUTE_CACHE_TABLE,
) -> int:
    return insert_run_results(
        conn,
        rows=rows,
        table_name=table_name,
        runs_table=runs_table,
        locations_table=locations_table,
        route_table=route_table,
    )
