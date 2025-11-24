# modules/infra/db/road_cache.py
# -*- coding: utf-8 -*-

"""
Road Legs Cache (DDL & DML).
============================

Manages the 'routes' table which caches generic A->B road distances.
Key: (origin_name, destiny_name, is_hgv)
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Iterable, Tuple

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.core import to_float, bool_to_int, int_to_bool
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

DEFAULT_TABLE = "routes"

# ────────────────────────────────────────────────────────────────────────────────
# Schema
# ────────────────────────────────────────────────────────────────────────────────

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_name         TEXT      NOT NULL
    , origin_lat          REAL
    , origin_lon          REAL
    , destiny_name        TEXT      NOT NULL
    , destiny_lat         REAL
    , destiny_lon         REAL
    , distance_km         REAL
    , is_hgv              INTEGER
    , insertion_timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_key 
    ON {table} (origin_name, destiny_name, is_hgv);
"""

def ensure_main_table(conn: sqlite3.Connection, table_name: str = DEFAULT_TABLE) -> None:
    """Idempotently create the routes table and indexes."""
    conn.execute(_DDL_SQL.format(table=table_name))
    conn.execute(_IDX_SQL.format(table=table_name))


# ────────────────────────────────────────────────────────────────────────────────
# Write Operations
# ────────────────────────────────────────────────────────────────────────────────

def upsert_run(
      conn: sqlite3.Connection
    , *
    , origin: str
    , destiny: str
    , origin_lat: Optional[float] = None
    , origin_lon: Optional[float] = None
    , destiny_lat: Optional[float] = None
    , destiny_lon: Optional[float] = None
    , distance_km: Optional[float] = None
    , is_hgv: Optional[bool] = None
    , table_name: str = DEFAULT_TABLE
) -> None:
    """Insert or Update a cached route leg."""
    ensure_main_table(conn, table_name)

    sql = f"""
    INSERT INTO {table_name} (
          origin_name, origin_lat, origin_lon
        , destiny_name, destiny_lat, destiny_lon
        , distance_km, is_hgv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(origin_name, destiny_name, is_hgv) DO UPDATE SET
          origin_lat=excluded.origin_lat
        , origin_lon=excluded.origin_lon
        , distance_km=excluded.distance_km
    """
    
    params = (
        origin, to_float(origin_lat), to_float(origin_lon),
        destiny, to_float(destiny_lat), to_float(destiny_lon),
        to_float(distance_km), bool_to_int(is_hgv)
    )
    conn.execute(sql, params)


def overwrite_keys(
      conn: sqlite3.Connection
    , *
    , keys: Iterable[Tuple[str, str, Optional[bool]]]
    , table_name: str = DEFAULT_TABLE
) -> int:
    """
    Delete specific keys to force a cache refresh.
    Keys format: (origin, destiny, is_hgv)
    """
    ensure_main_table(conn, table_name)
    
    # Split into two batches because NULL equality in SQL is tricky (IS NULL vs = 1)
    batch_null = []
    batch_val = []
    
    for o, d, h in keys:
        if h is None:
            batch_null.append((o, d))
        else:
            batch_val.append((o, d, bool_to_int(h)))
            
    count = 0
    if batch_null:
        sql = f"DELETE FROM {table_name} WHERE origin_name=? AND destiny_name=? AND is_hgv IS NULL"
        count += conn.executemany(sql, batch_null).rowcount
    if batch_val:
        sql = f"DELETE FROM {table_name} WHERE origin_name=? AND destiny_name=? AND is_hgv=?"
        count += conn.executemany(sql, batch_val).rowcount
        
    return count


def delete_key(
      conn: sqlite3.Connection
    , *
    , origin: str
    , destiny: str
    , is_hgv: Optional[bool] = None
    , table_name: str = DEFAULT_TABLE
) -> int:
    """
    Delete a single composite key. Convenience wrapper for overwrite_keys.
    """
    return overwrite_keys(
        conn, 
        keys=[(origin, destiny, is_hgv)], 
        table_name=table_name
    )


# ────────────────────────────────────────────────────────────────────────────────
# Read Operations
# ────────────────────────────────────────────────────────────────────────────────

def list_runs(
      conn: sqlite3.Connection
    , *
    , origin: Optional[str] = None
    , destiny: Optional[str] = None
    , table_name: str = DEFAULT_TABLE
    , limit: int = 100
) -> List[Dict[str, Any]]:
    """Query the cache with optional filters."""
    ensure_main_table(conn, table_name)
    
    clauses = []
    params = []
    
    if origin:
        clauses.append("origin_name = ?")
        params.append(origin)
    if destiny:
        clauses.append("destiny_name = ?")
        params.append(destiny)
        
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    
    sql = f"""
    SELECT origin_name, destiny_name, distance_km, is_hgv, origin_lat, origin_lon
    FROM {table_name} {where} LIMIT ?
    """
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "origin": r[0], "destiny": r[1],
            "distance_km": to_float(r[2]),
            "is_hgv": int_to_bool(r[3]),
            "origin_lat": to_float(r[4]), "origin_lon": to_float(r[5])
        }
        for r in rows
    ]


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.db.core import db_session
    print("--- Road Cache Smoke Test ---")
    
    with db_session(":memory:") as conn:
        upsert_run(conn, origin="A", destiny="B", distance_km=100.0, is_hgv=True)
        res = list_runs(conn)
        print(f"Stored: {res}")
        assert len(res) == 1
        assert res[0]['distance_km'] == 100.0
        
        delete_key(conn, origin="A", destiny="B", is_hgv=True)
        res2 = list_runs(conn)
        assert len(res2) == 0
        print("Delete successful.")
        
    print("--- Done ---")