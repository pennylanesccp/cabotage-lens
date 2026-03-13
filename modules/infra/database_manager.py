from __future__ import annotations

from modules.infra.db.bulk_results import (
    DEFAULT_TABLE as DEFAULT_BULK_RESULTS_TABLE,
    BulkResultRecord,
    BulkResultSummary,
    ensure_results_table as ensure_bulk_results_table,
    list_input_destiny_keys as list_bulk_result_input_destiny_keys,
    list_results as list_bulk_results,
    summarize_results as summarize_bulk_results,
    upsert_result as upsert_bulk_result,
    upsert_results as upsert_bulk_results,
)
from modules.infra.db.bulk_runs import (
    DEFAULT_RUNS_TABLE as DEFAULT_BULK_RUNS_TABLE,
    DEFAULT_RUN_RESULTS_TABLE as DEFAULT_BULK_RUN_RESULTS_TABLE,
    BulkRunRecord,
    BulkRunResultRecord,
    BulkRunSelector,
    ensure_run_results_table as ensure_bulk_run_results_table,
    ensure_runs_table as ensure_bulk_runs_table,
    finish_run as finish_bulk_run,
    get_latest_completed_run,
    insert_run_result as insert_bulk_run_result,
    insert_run_results as insert_bulk_run_results,
    list_available_cargo_values as list_bulk_run_cargo_values,
    list_available_origins as list_bulk_run_origins,
    list_run_results as list_bulk_run_results,
    start_run as start_bulk_run,
    upsert_run as upsert_bulk_run,
)
from modules.infra.db.core import connection_target_summary, connect, db_session
from modules.infra.db.multimodal import (
    ensure_results_table as ensure_multimodal_results_table,
    upsert_result as upsert_multimodal_result,
)
from modules.infra.db.place_points import (
    DEFAULT_TABLE as DEFAULT_PLACE_POINTS_TABLE,
    ensure_table as ensure_place_points_table,
    find_point as find_cached_place_point,
    list_points as list_cached_place_points,
    upsert_point as upsert_place_point,
    upsert_points as upsert_place_points,
)
from modules.infra.db.road_cache import (
    DEFAULT_TABLE,
    delete_key,
    ensure_main_table,
    find_place_point as find_route_place_point,
    get_run,
    get_run_by_coords,
    list_origin_names,
    list_place_names,
    list_place_points as list_route_place_points,
    list_runs,
    list_runs_by_coord_keys,
    list_runs_by_label_keys,
    overwrite_keys,
    upsert_run,
    upsert_runs,
)
from modules.infra.db.settings import load_database_settings

__all__ = [
    "DEFAULT_TABLE",
    "DEFAULT_PLACE_POINTS_TABLE",
    "DEFAULT_BULK_RESULTS_TABLE",
    "DEFAULT_BULK_RUNS_TABLE",
    "DEFAULT_BULK_RUN_RESULTS_TABLE",
    "BulkResultRecord",
    "BulkResultSummary",
    "BulkRunSelector",
    "BulkRunRecord",
    "BulkRunResultRecord",
    "connection_target_summary",
    "connect",
    "db_session",
    "load_database_settings",
    "ensure_main_table",
    "find_place_point",
    "find_route_place_point",
    "get_run",
    "get_run_by_coords",
    "list_runs_by_label_keys",
    "list_runs_by_coord_keys",
    "upsert_run",
    "upsert_runs",
    "list_origin_names",
    "list_route_place_points",
    "list_runs",
    "list_place_names",
    "overwrite_keys",
    "delete_key",
    "ensure_place_points_table",
    "find_cached_place_point",
    "list_cached_place_points",
    "upsert_place_point",
    "upsert_place_points",
    "ensure_multimodal_results_table",
    "upsert_multimodal_result",
    "ensure_bulk_results_table",
    "list_bulk_results",
    "list_bulk_result_input_destiny_keys",
    "summarize_bulk_results",
    "upsert_bulk_result",
    "upsert_bulk_results",
    "ensure_bulk_runs_table",
    "ensure_bulk_run_results_table",
    "start_bulk_run",
    "upsert_bulk_run",
    "finish_bulk_run",
    "insert_bulk_run_result",
    "insert_bulk_run_results",
    "get_latest_completed_run",
    "list_bulk_run_origins",
    "list_bulk_run_cargo_values",
    "list_bulk_run_results",
]


def find_place_point(conn, *, place: str, table_name: str = DEFAULT_PLACE_POINTS_TABLE):
    """Resolve a cached place point from the canonical location-alias cache."""
    cached = find_cached_place_point(conn, place=place, table_name=table_name)
    if cached is not None:
        return cached
    return find_route_place_point(conn, place=place)
