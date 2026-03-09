# -*- coding: utf-8 -*-

"""
Road distance cache.

This table is reusable infrastructure for resolved road legs. It is separate
from analytical evaluation outputs and is now designed to work on both
Supabase Postgres and legacy SQLite.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.addressing.text import ascii_place_key
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

DEFAULT_TABLE = "routes"
DEFAULT_PROFILE = "driving-hgv"
_LEGACY_INDEX_NAME = "uq_{table}_key"
_PROFILE_INDEX_NAME = "uq_{table}_requested_profile"
_COORDS_INDEX_NAME = "idx_{table}_coords_requested_profile"

_POSTGRES_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      id                  BIGSERIAL PRIMARY KEY
    , origin_key          TEXT      NOT NULL
    , origin_name         TEXT      NOT NULL
    , origin_lat          DOUBLE PRECISION
    , origin_lon          DOUBLE PRECISION
    , destiny_key         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , destiny_lat         DOUBLE PRECISION
    , destiny_lon         DOUBLE PRECISION
    , profile_requested   TEXT      NOT NULL DEFAULT 'driving-hgv'
    , profile_used        TEXT
    , lookup_mode         TEXT      NOT NULL DEFAULT 'label'
    , source              TEXT      NOT NULL DEFAULT 'ors'
    , distance_km         DOUBLE PRECISION
    , is_hgv              INTEGER
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_SQLITE_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_key          TEXT
    , origin_name         TEXT      NOT NULL
    , origin_lat          REAL
    , origin_lon          REAL
    , destiny_key         TEXT
    , destiny_name        TEXT      NOT NULL
    , destiny_lat         REAL
    , destiny_lon         REAL
    , profile_requested   TEXT      NOT NULL DEFAULT 'driving-hgv'
    , profile_used        TEXT
    , lookup_mode         TEXT      NOT NULL DEFAULT 'label'
    , source              TEXT      NOT NULL DEFAULT 'ors'
    , distance_km         REAL
    , is_hgv              INTEGER
    , insertion_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
    ON {table} (origin_key, destiny_key, profile_requested);
"""

_COORDS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS {index_name}
    ON {table} (profile_requested, origin_lat, origin_lon, destiny_lat, destiny_lon);
"""


def normalize_profile(profile: Optional[str]) -> str:
    text = str(profile or DEFAULT_PROFILE).strip().lower()
    return text or DEFAULT_PROFILE


def profile_is_hgv(profile: Optional[str]) -> bool:
    return normalize_profile(profile) == "driving-hgv"


def _build_place_key(label: Any) -> str:
    return ascii_place_key(label)


def _ensure_column(conn: DBConnection, table_name: str, column_name: str, ddl: str) -> None:
    if column_name in table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _backfill_profile_columns(conn: DBConnection, table_name: str) -> None:
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
             , lookup_mode = CASE
                   WHEN TRIM(COALESCE(lookup_mode, '')) <> '' THEN lookup_mode
                   ELSE 'label'
               END
             , source = CASE
                   WHEN TRIM(COALESCE(source, '')) <> '' THEN source
                   ELSE 'ors'
               END
             , updated_timestamp = COALESCE(updated_timestamp, insertion_timestamp, {current_timestamp_sql()})
        """
    )


def _backfill_route_keys(conn: DBConnection, table_name: str) -> None:
    rows = conn.execute(
        f"""
        SELECT DISTINCT
              origin_name
            , destiny_name
            , profile_requested
        FROM {table_name}
        WHERE TRIM(COALESCE(origin_key, '')) = ''
           OR TRIM(COALESCE(destiny_key, '')) = ''
        """
    ).fetchall()
    if not rows:
        return

    updates = [
        (
            _build_place_key(row[0]),
            _build_place_key(row[1]),
            row[0],
            row[1],
            normalize_profile(row[2]),
        )
        for row in rows
    ]
    conn.executemany(
        f"""
        UPDATE {table_name}
           SET origin_key = ?
             , destiny_key = ?
             , updated_timestamp = COALESCE(updated_timestamp, insertion_timestamp, {current_timestamp_sql()})
         WHERE origin_name = ?
           AND destiny_name = ?
           AND profile_requested = ?
        """,
        updates,
    )


def _drop_legacy_indexes(conn: DBConnection, table_name: str) -> None:
    conn.execute(f"DROP INDEX IF EXISTS {_LEGACY_INDEX_NAME.format(table=table_name)}")


def _dedupe_sqlite_rows(conn: DBConnection, table_name: str) -> None:
    if conn.backend != "sqlite":
        return
    conn.execute(
        f"""
        DELETE FROM {table_name}
         WHERE rowid NOT IN (
             SELECT MAX(rowid)
             FROM {table_name}
             WHERE TRIM(COALESCE(origin_key, '')) <> ''
               AND TRIM(COALESCE(destiny_key, '')) <> ''
               AND TRIM(COALESCE(profile_requested, '')) <> ''
             GROUP BY origin_key, destiny_key, profile_requested
         )
           AND TRIM(COALESCE(origin_key, '')) <> ''
           AND TRIM(COALESCE(destiny_key, '')) <> ''
           AND TRIM(COALESCE(profile_requested, '')) <> ''
        """
    )


def ensure_main_table(conn: DBConnection, table_name: str = DEFAULT_TABLE) -> None:
    """Create or migrate the road cache table in place."""
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "road_cache", table):
        return
    ddl = _POSTGRES_DDL_SQL if conn.backend == "postgres" else _SQLITE_DDL_SQL
    conn.execute(ddl.format(table=table))
    _ensure_column(conn, table, "origin_key", "origin_key TEXT")
    _ensure_column(conn, table, "destiny_key", "destiny_key TEXT")
    _ensure_column(conn, table, "profile_requested", "profile_requested TEXT")
    _ensure_column(conn, table, "profile_used", "profile_used TEXT")
    _ensure_column(conn, table, "lookup_mode", "lookup_mode TEXT")
    _ensure_column(conn, table, "source", "source TEXT")
    _ensure_column(conn, table, "updated_timestamp", "updated_timestamp TIMESTAMP")
    _backfill_profile_columns(conn, table)
    _backfill_route_keys(conn, table)
    _dedupe_sqlite_rows(conn, table)
    _drop_legacy_indexes(conn, table)
    conn.execute(
        _UNIQUE_INDEX_SQL.format(
            table=table,
            index_name=_PROFILE_INDEX_NAME.format(table=table),
        )
    )
    conn.execute(
        _COORDS_INDEX_SQL.format(
            table=table,
            index_name=_COORDS_INDEX_NAME.format(table=table),
        )
    )
    mark_schema_ready(conn, "road_cache", table)


def _row_to_dict(row: Sequence[Any]) -> Dict[str, Any]:
    return {
        "origin_key": row[0],
        "origin": row[1],
        "destiny_key": row[2],
        "destiny": row[3],
        "distance_km": to_float(row[4]),
        "is_hgv": int_to_bool(row[5]),
        "origin_lat": to_float(row[6]),
        "origin_lon": to_float(row[7]),
        "destiny_lat": to_float(row[8]),
        "destiny_lon": to_float(row[9]),
        "profile_requested": str(row[10] or DEFAULT_PROFILE),
        "profile_used": (None if row[11] in (None, "") else str(row[11])),
        "lookup_mode": (None if row[12] in (None, "") else str(row[12])),
        "source": (None if row[13] in (None, "") else str(row[13])),
        "insertion_timestamp": row[14],
        "updated_timestamp": row[15],
    }


def upsert_run(
    conn: DBConnection,
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
    lookup_mode: str = "label",
    source: str = "ors",
    is_hgv: Optional[bool] = None,
    table_name: str = DEFAULT_TABLE,
) -> None:
    """Insert or update one cached road leg."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    requested = normalize_profile(profile_requested)
    used = normalize_profile(profile_used) if profile_used else None
    final_is_hgv = is_hgv if is_hgv is not None else (profile_is_hgv(used) if used else None)
    origin_key = _build_place_key(origin)
    destiny_key = _build_place_key(destiny)

    sql = f"""
    INSERT INTO {table} (
          origin_key, origin_name, origin_lat, origin_lon
        , destiny_key, destiny_name, destiny_lat, destiny_lon
        , profile_requested, profile_used
        , lookup_mode, source
        , distance_km, is_hgv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(origin_key, destiny_key, profile_requested) DO UPDATE SET
          origin_name=excluded.origin_name
        , origin_lat=excluded.origin_lat
        , origin_lon=excluded.origin_lon
        , destiny_name=excluded.destiny_name
        , destiny_lat=excluded.destiny_lat
        , destiny_lon=excluded.destiny_lon
        , profile_used=excluded.profile_used
        , lookup_mode=excluded.lookup_mode
        , source=excluded.source
        , distance_km=excluded.distance_km
        , is_hgv=excluded.is_hgv
        , updated_timestamp={current_timestamp_sql()}
    """

    params = (
        origin_key,
        origin,
        to_float(origin_lat),
        to_float(origin_lon),
        destiny_key,
        destiny,
        to_float(destiny_lat),
        to_float(destiny_lon),
        requested,
        used,
        str(lookup_mode or "label").strip().lower() or "label",
        str(source or "ors").strip().lower() or "ors",
        to_float(distance_km),
        bool_to_int(final_is_hgv),
    )
    conn.execute(sql, params)


def get_run(
    conn: DBConnection,
    *,
    origin: str,
    destiny: str,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
) -> Optional[Dict[str, Any]]:
    """Fetch one exact cached leg for the requested routing profile."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    requested = normalize_profile(profile_requested)
    row = conn.execute(
        f"""
        SELECT
              origin_key
            , origin_name
            , destiny_key
            , destiny_name
            , distance_km
            , is_hgv
            , origin_lat
            , origin_lon
            , destiny_lat
            , destiny_lon
            , profile_requested
            , profile_used
            , lookup_mode
            , source
            , insertion_timestamp
            , updated_timestamp
        FROM {table}
        WHERE origin_key = ?
          AND destiny_key = ?
          AND profile_requested = ?
        LIMIT 1
        """,
        (_build_place_key(origin), _build_place_key(destiny), requested),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def get_run_by_coords(
    conn: DBConnection,
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
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    requested = normalize_profile(profile_requested)
    row = conn.execute(
        f"""
        SELECT
              origin_key
            , origin_name
            , destiny_key
            , destiny_name
            , distance_km
            , is_hgv
            , origin_lat
            , origin_lon
            , destiny_lat
            , destiny_lon
            , profile_requested
            , profile_used
            , lookup_mode
            , source
            , insertion_timestamp
            , updated_timestamp
        FROM {table}
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
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[str, str, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
) -> int:
    """Delete specific requested-profile cache keys."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    rows = [(_build_place_key(o), _build_place_key(d), normalize_profile(p)) for o, d, p in keys]
    if not rows:
        return 0
    sql = f"""
    DELETE FROM {table}
    WHERE origin_key = ?
      AND destiny_key = ?
      AND profile_requested = ?
    """
    cur = conn.executemany(sql, rows)
    return int(cur.rowcount or 0)


def delete_key(
    conn: DBConnection,
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
    conn: DBConnection,
    *,
    origin: Optional[str] = None,
    destiny: Optional[str] = None,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List cached road legs with optional filters."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    clauses: List[str] = []
    params: List[Any] = []

    if origin:
        clauses.append("origin_key = ?")
        params.append(_build_place_key(origin))
    if destiny:
        clauses.append("destiny_key = ?")
        params.append(_build_place_key(destiny))
    if profile_requested:
        clauses.append("profile_requested = ?")
        params.append(normalize_profile(profile_requested))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
    SELECT
          origin_key
        , origin_name
        , destiny_key
        , destiny_name
        , distance_km
        , is_hgv
        , origin_lat
        , origin_lon
        , destiny_lat
        , destiny_lon
        , profile_requested
        , profile_used
        , lookup_mode
        , source
        , insertion_timestamp
        , updated_timestamp
    FROM {table}
    {where}
    ORDER BY updated_timestamp DESC, insertion_timestamp DESC
    LIMIT ?
    """
    params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_place_names(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_TABLE,
    limit: int = 10_000,
) -> List[str]:
    """Return distinct cached origin/destination labels."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    sql = f"""
    SELECT name
    FROM (
        SELECT TRIM(origin_name) AS name FROM {table}
        UNION
        SELECT TRIM(destiny_name) AS name FROM {table}
    )
    WHERE name IS NOT NULL AND name <> ''
    ORDER BY LOWER(name) ASC
    LIMIT ?
    """
    rows = conn.execute(sql, (int(limit),)).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


if __name__ == "__main__":
    from modules.infra.db.core import db_session

    print("--- Road Cache Smoke Test ---")

    with db_session("smoke_test_routes.sqlite", backend="sqlite") as conn:
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

    Path("smoke_test_routes.sqlite").unlink(missing_ok=True)
    print("--- Done ---")
