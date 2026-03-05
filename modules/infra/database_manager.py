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
    , connect
    , db_session
)

# 2. Road Caching (Routes Table)
from modules.infra.db.road_cache import (
      DEFAULT_TABLE
    , ensure_main_table
    , upsert_run
    , list_runs
    , list_place_names
    , overwrite_keys
    , delete_key
)

# 3. Multimodal Results
from modules.infra.db.multimodal import (
      ensure_results_table as ensure_multimodal_results_table
    , upsert_result as upsert_multimodal_result
)

# Export public API
__all__ = [
    "DEFAULT_DB_PATH", "DEFAULT_TABLE",
    "connect", "db_session",
    "ensure_main_table", "upsert_run", "list_runs", "list_place_names", "overwrite_keys", "delete_key",
    "ensure_multimodal_results_table", "upsert_multimodal_result"
]

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
        with db_session(":memory:") as conn:
            ensure_main_table(conn)
            upsert_run(conn, origin="A", destiny="B", distance_km=50.5, is_hgv=True)
            runs = list_runs(conn)
            log.info(f"Retrieved run: {runs[0]}")
            
            delete_key(conn, origin="A", destiny="B", is_hgv=True)
            
            ensure_multimodal_results_table(conn, "test_mm")
            upsert_multimodal_result(
                conn, "test_mm", 
                origin_name="A", destiny_name="B", cargo_t=100,
                road_fuel_cost_r=5000, delta_cost_r=-500
            )
            log.info("Multimodal result inserted via facade.")
            
        print("âœ… Facade test passed.")
        
    except Exception as e:
        log.error(f"âŒ Facade test failed: {e}")
        raise
