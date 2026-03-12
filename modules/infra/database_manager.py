# modules/infra/database_manager.py
# -*- coding: utf-8 -*-

"""
Database Manager (Facade).
==========================

This module aggregates the split database implementation into a single
importable interface, maintaining backward compatibility with existing code.

Implementation details are in `modules/infra/db/`.
"""

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 1. Core Connectivity
from modules.infra.db.core import (
      DEFAULT_DB_PATH
    , connection_target_summary
    , connect
    , db_session
)
from modules.infra.db.settings import load_database_settings

# 2. Road Caching (Routes Table)
from modules.infra.db.road_cache import (
      DEFAULT_TABLE
    , ensure_main_table
    , find_place_point as find_route_place_point
    , get_run
    , get_run_by_coords
    , list_runs_by_coord_keys
    , list_runs_by_label_keys
    , upsert_run
    , upsert_runs
    , list_origin_names
    , list_place_points as list_route_place_points
    , list_runs
    , list_place_names
    , overwrite_keys
    , delete_key
)
from modules.infra.db.place_points import (
      DEFAULT_TABLE as DEFAULT_PLACE_POINTS_TABLE
    , ensure_table as ensure_place_points_table
    , find_point as find_cached_place_point
    , list_points as list_cached_place_points
    , upsert_point as upsert_place_point
    , upsert_points as upsert_place_points
)

# 3. Multimodal Results
from modules.infra.db.multimodal import (
      ensure_results_table as ensure_multimodal_results_table
    , upsert_result as upsert_multimodal_result
)

# 4. Bulk Evaluation Results
from modules.infra.db.bulk_results import (
      DEFAULT_TABLE as DEFAULT_BULK_RESULTS_TABLE
    , BulkResultRecord
    , BulkResultSummary
    , ensure_results_table as ensure_bulk_results_table
    , list_input_destiny_keys as list_bulk_result_input_destiny_keys
    , list_results as list_bulk_results
    , summarize_results as summarize_bulk_results
    , upsert_result as upsert_bulk_result
    , upsert_results as upsert_bulk_results
)
from modules.infra.db.bulk_runs import (
      DEFAULT_RUNS_TABLE as DEFAULT_BULK_RUNS_TABLE
    , DEFAULT_RUN_RESULTS_TABLE as DEFAULT_BULK_RUN_RESULTS_TABLE
    , BulkRunRecord
    , BulkRunResultRecord
    , BulkRunSelector
    , ensure_runs_table as ensure_bulk_runs_table
    , ensure_run_results_table as ensure_bulk_run_results_table
    , finish_run as finish_bulk_run
    , get_latest_completed_run
    , insert_run_result as insert_bulk_run_result
    , insert_run_results as insert_bulk_run_results
    , list_available_cargo_values as list_bulk_run_cargo_values
    , list_available_origins as list_bulk_run_origins
    , list_run_results as list_bulk_run_results
    , start_run as start_bulk_run
    , upsert_run as upsert_bulk_run
)

# Export public API
__all__ = [
    "DEFAULT_DB_PATH", "DEFAULT_TABLE",
    "connection_target_summary", "connect", "db_session", "load_database_settings",
    "ensure_main_table", "find_place_point", "find_route_place_point", "get_run", "get_run_by_coords", "upsert_run",
    "list_runs_by_label_keys", "list_runs_by_coord_keys", "upsert_runs",
    "list_origin_names", "list_route_place_points", "list_runs", "list_place_names", "overwrite_keys", "delete_key",
    "DEFAULT_PLACE_POINTS_TABLE", "ensure_place_points_table", "find_cached_place_point",
    "list_cached_place_points", "upsert_place_point", "upsert_place_points",
    "ensure_multimodal_results_table", "upsert_multimodal_result",
    "DEFAULT_BULK_RESULTS_TABLE", "BulkResultRecord", "BulkResultSummary",
    "ensure_bulk_results_table", "list_bulk_results", "list_bulk_result_input_destiny_keys",
    "summarize_bulk_results", "upsert_bulk_result", "upsert_bulk_results",
    "DEFAULT_BULK_RUNS_TABLE", "DEFAULT_BULK_RUN_RESULTS_TABLE",
    "BulkRunSelector", "BulkRunRecord", "BulkRunResultRecord",
    "ensure_bulk_runs_table", "ensure_bulk_run_results_table",
    "start_bulk_run", "upsert_bulk_run", "finish_bulk_run", "insert_bulk_run_result", "insert_bulk_run_results",
    "get_latest_completed_run", "list_bulk_run_origins", "list_bulk_run_cargo_values", "list_bulk_run_results",
]


def find_place_point(conn, *, place: str, table_name: str = DEFAULT_PLACE_POINTS_TABLE):
    """
    Resolve a cached place point from the dedicated place-points table first,
    falling back to the latest routed coordinate in the shared road cache.
    """
    cached = find_cached_place_point(conn, place=place, table_name=table_name)
    if cached is not None:
        return cached
    return find_route_place_point(conn, place=place)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Smoke Test (Integration)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging, get_logger
    
    init_logging(level="INFO")
    log = get_logger("db_facade_test")
    
    print("--- Facade Integration Test ---")
    
    try:
        # Test the facade works by using the imported symbols
        with db_session(":memory:", backend="sqlite") as conn:
            ensure_main_table(conn)
            upsert_run(
                conn,
                origin="A",
                destiny="B",
                distance_km=50.5,
                profile_requested="driving-hgv",
                profile_used="driving-hgv",
            )
            runs = list_runs(conn)
            log.info(f"Retrieved run: {runs[0]}")
            
            delete_key(conn, origin="A", destiny="B", profile_requested="driving-hgv")
            
            ensure_multimodal_results_table(conn, "test_mm")
            upsert_multimodal_result(
                conn, "test_mm", 
                origin_name="A", destiny_name="B", cargo_t=100,
                road_fuel_cost_r=5000, delta_cost_r=-500
            )
            log.info("Multimodal result inserted via facade.")

            ensure_bulk_results_table(conn)
            upsert_bulk_result(
                conn,
                scenario_key="demo",
                origin_name="A",
                destiny_name="B",
                input_origin="A",
                input_destiny="B",
                cargo_t=100,
                truck_key="semi_27t",
                ors_profile="driving-hgv",
                status="ok",
            )
            log.info("Bulk result inserted via facade.")
            
        print("âœ… Facade test passed.")
        
    except Exception as e:
        log.error(f"âŒ Facade test failed: {e}")
        raise
