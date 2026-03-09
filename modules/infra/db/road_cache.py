# modules/infra/db/road_cache.py
# -*- coding: utf-8 -*-

"""
Road distance cache stored in SQLite.

This table is an infrastructure cache for resolved road legs. It is intentionally
separate from analytical evaluation results.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.core import bool_to_int, int_to_bool, to_float
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

DEFAULT_TABLE = "routes"
DEFAULT_PROFILE = "driving-hgv"
_LEGACY_INDEX_NAME = "uq_{table}_key"
_PROFILE_INDEX_NAME = "uq_{table}_requested_profile"

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_name         TEXT      NOT NULL
    , origin_lat          REAL
    , origin_lon          REAL
    , destiny_name        TEXT      NOT NULL
    , destiny_lat         REAL
    , destiny_lon         REAL
    , profile_requested   TEXT      NOT NULL DEFAULT 'driving-hgv'
    , profile_used        TEXT
    , distance_km         REAL
    , is_hgv              INTEGER
    , insertion_timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now'))
    , updated_timestamp   TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
    ON {table} (origin_name, destiny_name, profile_requested);
"""


def normalize_profile(profile: Optional[str]) -> str:
    text = str(profile or DEFAULT_PROFILE).strip().lower()
    return text or DEFAULT_PROFILE


def profile_is_hgv(profile: Optional[str]) -> bool:
    return normalize_profile(profile) == "driving-hgv"


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    cols = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})")}
    if column_name in cols:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _backfill_profile_columns(conn: sqlite3.Connection, table_name: str) -> None:
    conn.execute(
        f"""
        UPDATE {table_name}
           SET profile_requested = CASE
                   WHEN TRIM(COALESCE(profile_requested, '')) <> '' THEN LOWER(TRIM(profile_requested))
                   WHEN is_hgv = 1 THEN 'driving-hgv'
                   WHEN is_hgv = 0 THEN 'driving-car'
                   ELSE '{DEFAULT_PROFILE}'
               END
             , profile_used = CASE
                   WHEN TRIM(COALESCE(profile_used, '')) <> '' THEN LOWER(TRIM(profile_used))
                   WHEN is_hgv = 1 THEN 'driving-hgv'
                   WHEN is_hgv = 0 THEN 'driving-car'
                   ELSE profile_used
               END
             , updated_timestamp = COALESCE(updated_timestamp, insertion_timestamp, datetime('now'))
        """
    )


def ensure_main_table(conn: sqlite3.Connection, table_name: str = DEFAULT_TABLE) -> None:
    """Create or migrate the road cache table in place."""
    conn.execute(_DDL_SQL.format(table=table_name))
    _ensure_column(conn, table_name, "profile_requested", "profile_requested TEXT")
    _ensure_column(conn, table_name, "profile_used", "profile_used TEXT")
    _ensure_column(conn, table_name, "updated_timestamp", "updated_timestamp TIMESTAMP")
    _backfill_profile_columns(conn, table_name)
    conn.execute(f"DROP INDEX IF EXISTS {_LEGACY_INDEX_NAME.format(table=table_name)}")
    conn.execute(
        _IDX_SQL.format(
            table=table_name,
            index_name=_PROFILE_INDEX_NAME.format(table=table_name),
        )
    )


def _row_to_dict(row: Sequence[Any]) -> Dict[str, Any]:
    return {
        "origin": row[0],
        "destiny": row[1],
        "distance_km": to_float(row[2]),
        "is_hgv": int_to_bool(row[3]),
        "origin_lat": to_float(row[4]),
        "origin_lon": to_float(row[5]),
        "destiny_lat": to_float(row[6]),
        "destiny_lon": to_float(row[7]),
        "profile_requested": str(row[8] or DEFAULT_PROFILE),
        "profile_used": (None if row[9] in (None, "") else str(row[9])),
        "insertion_timestamp": row[10],
        "updated_timestamp": row[11],
    }


def upsert_run(
    conn: sqlite3.Connection,
    *,
    origin: str,
    destiny: str,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    destiny_lat: Optional[float] = None,
    destiny_lon: Optional[float] = None,
    distance_km: Optional[float] = None,
    profile_requested: Optional[str] = None,
    profile_used: Optional[str] = None,
    is_hgv: Optional[bool] = None,
    table_name: str = DEFAULT_TABLE,
) -> None:
    """Insert or update one cached road leg."""
    ensure_main_table(conn, table_name)

    requested = normalize_profile(profile_requested)
    used = normalize_profile(profile_used) if profile_used else None
    final_is_hgv = is_hgv if is_hgv is not None else (profile_is_hgv(used) if used else None)

    sql = f"""
    INSERT INTO {table_name} (
          origin_name, origin_lat, origin_lon
        , destiny_name, destiny_lat, destiny_lon
        , profile_requested, profile_used
        , distance_km, is_hgv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(origin_name, destiny_name, profile_requested) DO UPDATE SET
          origin_lat=excluded.origin_lat
        , origin_lon=excluded.origin_lon
        , destiny_lat=excluded.destiny_lat
        , destiny_lon=excluded.destiny_lon
        , profile_used=excluded.profile_used
        , distance_km=excluded.distance_km
        , is_hgv=excluded.is_hgv
        , updated_timestamp=datetime('now')
    """

    params = (
        origin,
        to_float(origin_lat),
        to_float(origin_lon),
        destiny,
        to_float(destiny_lat),
        to_float(destiny_lon),
        requested,
        used,
        to_float(distance_km),
        bool_to_int(final_is_hgv),
    )
    conn.execute(sql, params)


def get_run(
    conn: sqlite3.Connection,
    *,
    origin: str,
    destiny: str,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
) -> Optional[Dict[str, Any]]:
    """Fetch one exact cached leg for the requested routing profile."""
    ensure_main_table(conn, table_name)
    requested = normalize_profile(profile_requested)
    row = conn.execute(
        f"""
        SELECT
              origin_name
            , destiny_name
            , distance_km
            , is_hgv
            , origin_lat
            , origin_lon
            , destiny_lat
            , destiny_lon
            , profile_requested
            , profile_used
            , insertion_timestamp
            , updated_timestamp
        FROM {table_name}
        WHERE origin_name = ?
          AND destiny_name = ?
          AND profile_requested = ?
        LIMIT 1
        """,
        (origin, destiny, requested),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def get_run_by_coords(
    conn: sqlite3.Connection,
    *,
    origin_lat: float,
    origin_lon: float,
    destiny_lat: float,
    destiny_lon: float,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    tolerance_deg: float = 1e-5,
) -> Optional[Dict[str, Any]]:
    """Fetch one cached leg by coordinates when labels are unstable."""
    ensure_main_table(conn, table_name)
    requested = normalize_profile(profile_requested)
    row = conn.execute(
        f"""
        SELECT
              origin_name
            , destiny_name
            , distance_km
            , is_hgv
            , origin_lat
            , origin_lon
            , destiny_lat
            , destiny_lon
            , profile_requested
            , profile_used
            , insertion_timestamp
            , updated_timestamp
        FROM {table_name}
        WHERE profile_requested = ?
          AND origin_lat IS NOT NULL
          AND origin_lon IS NOT NULL
          AND destiny_lat IS NOT NULL
          AND destiny_lon IS NOT NULL
          AND ABS(origin_lat - ?) <= ?
          AND ABS(origin_lon - ?) <= ?
          AND ABS(destiny_lat - ?) <= ?
          AND ABS(destiny_lon - ?) <= ?
        ORDER BY updated_timestamp DESC, insertion_timestamp DESC
        LIMIT 1
        """,
        (
            requested,
            float(origin_lat),
            float(tolerance_deg),
            float(origin_lon),
            float(tolerance_deg),
            float(destiny_lat),
            float(tolerance_deg),
            float(destiny_lon),
            float(tolerance_deg),
        ),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def overwrite_keys(
    conn: sqlite3.Connection,
    *,
    keys: Iterable[Tuple[str, str, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
) -> int:
    """Delete specific requested-profile cache keys."""
    ensure_main_table(conn, table_name)
    rows = [(o, d, normalize_profile(p)) for o, d, p in keys]
    if not rows:
        return 0
    sql = f"""
    DELETE FROM {table_name}
    WHERE origin_name = ?
      AND destiny_name = ?
      AND profile_requested = ?
    """
    cur = conn.executemany(sql, rows)
    return int(cur.rowcount or 0)


def delete_key(
    conn: sqlite3.Connection,
    *,
    origin: str,
    destiny: str,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
) -> int:
    return overwrite_keys(
        conn,
        keys=[(origin, destiny, profile_requested)],
        table_name=table_name,
    )


def list_runs(
    conn: sqlite3.Connection,
    *,
    origin: Optional[str] = None,
    destiny: Optional[str] = None,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List cached road legs with optional filters."""
    ensure_main_table(conn, table_name)

    clauses: List[str] = []
    params: List[Any] = []

    if origin:
        clauses.append("origin_name = ?")
        params.append(origin)
    if destiny:
        clauses.append("destiny_name = ?")
        params.append(destiny)
    if profile_requested:
        clauses.append("profile_requested = ?")
        params.append(normalize_profile(profile_requested))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
    SELECT
          origin_name
        , destiny_name
        , distance_km
        , is_hgv
        , origin_lat
        , origin_lon
        , destiny_lat
        , destiny_lon
        , profile_requested
        , profile_used
        , insertion_timestamp
        , updated_timestamp
    FROM {table_name}
    {where}
    ORDER BY updated_timestamp DESC, insertion_timestamp DESC
    LIMIT ?
    """
    params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_place_names(
    conn: sqlite3.Connection,
    *,
    table_name: str = DEFAULT_TABLE,
    limit: int = 10_000,
) -> List[str]:
    """Return distinct cached origin/destination labels."""
    ensure_main_table(conn, table_name)

    sql = f"""
    SELECT name
    FROM (
        SELECT TRIM(origin_name) AS name FROM {table_name}
        UNION
        SELECT TRIM(destiny_name) AS name FROM {table_name}
    )
    WHERE name IS NOT NULL AND name <> ''
    ORDER BY name COLLATE NOCASE ASC
    LIMIT ?
    """
    rows = conn.execute(sql, (int(limit),)).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


if __name__ == "__main__":
    from modules.infra.db.core import db_session

    print("--- Road Cache Smoke Test ---")

    with db_session(":memory:") as conn:
        upsert_run(
            conn,
            origin="A",
            destiny="B",
            distance_km=100.0,
            profile_requested="driving-hgv",
            profile_used="driving-hgv",
        )
        row = get_run(conn, origin="A", destiny="B", profile_requested="driving-hgv")
        print(f"Stored: {row}")
        assert row is not None
        assert row["distance_km"] == 100.0

        delete_key(conn, origin="A", destiny="B", profile_requested="driving-hgv")
        rows = list_runs(conn)
        assert len(rows) == 0
        print("Delete successful.")

    print("--- Done ---")
