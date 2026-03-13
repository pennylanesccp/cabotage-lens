# -*- coding: utf-8 -*-

"""
Road distance cache.

This table is reusable infrastructure for resolved road legs. It is separate
from analytical evaluation outputs and persists only in Supabase Postgres.
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
_COORD_KEYS_INDEX_NAME = "idx_{table}_coord_keys_requested_profile"
_COORD_PRECISION = 5

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
    , origin_coord_key    TEXT
    , destiny_coord_key   TEXT
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

_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
    ON {table} (origin_key, destiny_key, profile_requested);
"""

_COORDS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS {index_name}
    ON {table} (profile_requested, origin_lat, origin_lon, destiny_lat, destiny_lon);
"""

_COORD_KEYS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS {index_name}
    ON {table} (profile_requested, origin_coord_key, destiny_coord_key);
"""


def normalize_profile(profile: Optional[str]) -> str:
    text = str(profile or DEFAULT_PROFILE).strip().lower()
    return text or DEFAULT_PROFILE


def profile_is_hgv(profile: Optional[str]) -> bool:
    return normalize_profile(profile) == "driving-hgv"


def _build_place_key(label: Any) -> str:
    return ascii_place_key(label)


def _coord_key(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    lat_value = to_float(lat)
    lon_value = to_float(lon)
    if lat_value is None or lon_value is None:
        return None
    return f"{lat_value:.{_COORD_PRECISION}f},{lon_value:.{_COORD_PRECISION}f}"


def build_label_lookup_key(origin: str, destiny: str, profile_requested: Optional[str]) -> tuple[str, str, str]:
    return (_build_place_key(origin), _build_place_key(destiny), normalize_profile(profile_requested))


def build_coord_lookup_key(
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    destiny_lat: Optional[float],
    destiny_lon: Optional[float],
    profile_requested: Optional[str],
) -> Optional[tuple[str, str, str]]:
    origin_coord_key = _coord_key(origin_lat, origin_lon)
    destiny_coord_key = _coord_key(destiny_lat, destiny_lon)
    if origin_coord_key is None or destiny_coord_key is None:
        return None
    return (normalize_profile(profile_requested), origin_coord_key, destiny_coord_key)


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


def _backfill_coord_keys(conn: DBConnection, table_name: str) -> None:
    rows = conn.execute(
        f"""
        SELECT DISTINCT
              origin_name
            , destiny_name
            , profile_requested
            , origin_lat
            , origin_lon
            , destiny_lat
            , destiny_lon
        FROM {table_name}
        WHERE (
                origin_lat IS NOT NULL
            AND origin_lon IS NOT NULL
            AND destiny_lat IS NOT NULL
            AND destiny_lon IS NOT NULL
        )
          AND (
                TRIM(COALESCE(origin_coord_key, '')) = ''
             OR TRIM(COALESCE(destiny_coord_key, '')) = ''
          )
        """
    ).fetchall()
    if not rows:
        return

    updates = []
    for row in rows:
        origin_coord_key = _coord_key(row[3], row[4])
        destiny_coord_key = _coord_key(row[5], row[6])
        if origin_coord_key is None or destiny_coord_key is None:
            continue
        updates.append(
            (
                origin_coord_key,
                destiny_coord_key,
                row[0],
                row[1],
                normalize_profile(row[2]),
            )
        )
    if not updates:
        return

    conn.executemany(
        f"""
        UPDATE {table_name}
           SET origin_coord_key = ?
             , destiny_coord_key = ?
             , updated_timestamp = COALESCE(updated_timestamp, insertion_timestamp, {current_timestamp_sql()})
         WHERE origin_name = ?
           AND destiny_name = ?
           AND profile_requested = ?
        """,
        updates,
    )


def _drop_legacy_indexes(conn: DBConnection, table_name: str) -> None:
    conn.execute(f"DROP INDEX IF EXISTS {_LEGACY_INDEX_NAME.format(table=table_name)}")


def ensure_main_table(conn: DBConnection, table_name: str = DEFAULT_TABLE) -> None:
    """Create or migrate the road cache table in place."""
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "road_cache", table):
        return
    conn.execute(_POSTGRES_DDL_SQL.format(table=table))
    _ensure_column(conn, table, "origin_key", "origin_key TEXT")
    _ensure_column(conn, table, "destiny_key", "destiny_key TEXT")
    _ensure_column(conn, table, "origin_coord_key", "origin_coord_key TEXT")
    _ensure_column(conn, table, "destiny_coord_key", "destiny_coord_key TEXT")
    _ensure_column(conn, table, "profile_requested", "profile_requested TEXT")
    _ensure_column(conn, table, "profile_used", "profile_used TEXT")
    _ensure_column(conn, table, "lookup_mode", "lookup_mode TEXT")
    _ensure_column(conn, table, "source", "source TEXT")
    _ensure_column(conn, table, "updated_timestamp", "updated_timestamp TIMESTAMPTZ")
    _backfill_profile_columns(conn, table)
    _backfill_route_keys(conn, table)
    _backfill_coord_keys(conn, table)
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
    conn.execute(
        _COORD_KEYS_INDEX_SQL.format(
            table=table,
            index_name=_COORD_KEYS_INDEX_NAME.format(table=table),
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
        "origin_coord_key": (None if row[10] in (None, "") else str(row[10])),
        "destiny_coord_key": (None if row[11] in (None, "") else str(row[11])),
        "profile_requested": str(row[12] or DEFAULT_PROFILE),
        "profile_used": (None if row[13] in (None, "") else str(row[13])),
        "lookup_mode": (None if row[14] in (None, "") else str(row[14])),
        "source": (None if row[15] in (None, "") else str(row[15])),
        "insertion_timestamp": row[16],
        "updated_timestamp": row[17],
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
    origin_coord_key = _coord_key(origin_lat, origin_lon)
    destiny_coord_key = _coord_key(destiny_lat, destiny_lon)

    sql = f"""
    INSERT INTO {table} (
          origin_key, origin_name, origin_lat, origin_lon
        , destiny_key, destiny_name, destiny_lat, destiny_lon
        , origin_coord_key, destiny_coord_key
        , profile_requested, profile_used
        , lookup_mode, source
        , distance_km, is_hgv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(origin_key, destiny_key, profile_requested) DO UPDATE SET
          origin_name=excluded.origin_name
        , origin_lat=excluded.origin_lat
        , origin_lon=excluded.origin_lon
        , destiny_name=excluded.destiny_name
        , destiny_lat=excluded.destiny_lat
        , destiny_lon=excluded.destiny_lon
        , origin_coord_key=excluded.origin_coord_key
        , destiny_coord_key=excluded.destiny_coord_key
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
        origin_coord_key,
        destiny_coord_key,
        requested,
        used,
        str(lookup_mode or "label").strip().lower() or "label",
        str(source or "ors").strip().lower() or "ors",
        to_float(distance_km),
        bool_to_int(final_is_hgv),
    )
    conn.execute(sql, params)


def upsert_runs(
    conn: DBConnection,
    *,
    rows: Iterable[Dict[str, Any]],
    table_name: str = DEFAULT_TABLE,
) -> int:
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    sql = f"""
    INSERT INTO {table} (
          origin_key, origin_name, origin_lat, origin_lon
        , destiny_key, destiny_name, destiny_lat, destiny_lon
        , origin_coord_key, destiny_coord_key
        , profile_requested, profile_used
        , lookup_mode, source
        , distance_km, is_hgv
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(origin_key, destiny_key, profile_requested) DO UPDATE SET
          origin_name=excluded.origin_name
        , origin_lat=excluded.origin_lat
        , origin_lon=excluded.origin_lon
        , destiny_name=excluded.destiny_name
        , destiny_lat=excluded.destiny_lat
        , destiny_lon=excluded.destiny_lon
        , origin_coord_key=excluded.origin_coord_key
        , destiny_coord_key=excluded.destiny_coord_key
        , profile_used=excluded.profile_used
        , lookup_mode=excluded.lookup_mode
        , source=excluded.source
        , distance_km=excluded.distance_km
        , is_hgv=excluded.is_hgv
        , updated_timestamp={current_timestamp_sql()}
    """

    params_list: list[tuple[Any, ...]] = []
    for row in rows:
        origin = str(row.get("origin") or "").strip()
        destiny = str(row.get("destiny") or "").strip()
        if not origin or not destiny:
            continue
        profile_requested = normalize_profile(row.get("profile_requested"))
        profile_used = normalize_profile(row.get("profile_used")) if row.get("profile_used") else None
        final_is_hgv = row.get("is_hgv")
        if final_is_hgv is None and profile_used:
            final_is_hgv = profile_is_hgv(profile_used)
        origin_lat = to_float(row.get("origin_lat"))
        origin_lon = to_float(row.get("origin_lon"))
        destiny_lat = to_float(row.get("destiny_lat"))
        destiny_lon = to_float(row.get("destiny_lon"))
        params_list.append(
            (
                _build_place_key(origin),
                origin,
                origin_lat,
                origin_lon,
                _build_place_key(destiny),
                destiny,
                destiny_lat,
                destiny_lon,
                _coord_key(origin_lat, origin_lon),
                _coord_key(destiny_lat, destiny_lon),
                profile_requested,
                profile_used,
                str(row.get("lookup_mode") or "label").strip().lower() or "label",
                str(row.get("source") or "ors").strip().lower() or "ors",
                to_float(row.get("distance_km")),
                bool_to_int(final_is_hgv),
            )
        )

    if not params_list:
        return 0

    conn.executemany(sql, params_list)
    return len(params_list)


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
            , origin_coord_key
            , destiny_coord_key
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
    coord_lookup_key = build_coord_lookup_key(
        origin_lat,
        origin_lon,
        destiny_lat,
        destiny_lon,
        requested,
    )
    row = None
    if coord_lookup_key is not None:
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
                , origin_coord_key
                , destiny_coord_key
                , profile_requested
                , profile_used
                , lookup_mode
                , source
                , insertion_timestamp
                , updated_timestamp
            FROM {table}
            WHERE profile_requested = ?
              AND origin_coord_key = ?
              AND destiny_coord_key = ?
            ORDER BY updated_timestamp DESC, insertion_timestamp DESC
            LIMIT 1
            """,
            coord_lookup_key,
        ).fetchone()
    if row is None:
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
                , origin_coord_key
                , destiny_coord_key
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


def list_runs_by_label_keys(
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[str, str, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    prepared = [build_label_lookup_key(origin, destiny, profile_requested) for origin, destiny, profile_requested in keys]
    if not prepared:
        return {}

    placeholders = ", ".join(["(?, ?, ?)"] * len(prepared))
    flat_params: list[Any] = []
    for row in prepared:
        flat_params.extend(row)

    rows = conn.execute(
        f"""
        WITH wanted(origin_key, destiny_key, profile_requested) AS (
            VALUES {placeholders}
        )
        SELECT
              r.origin_key
            , r.origin_name
            , r.destiny_key
            , r.destiny_name
            , r.distance_km
            , r.is_hgv
            , r.origin_lat
            , r.origin_lon
            , r.destiny_lat
            , r.destiny_lon
            , r.origin_coord_key
            , r.destiny_coord_key
            , r.profile_requested
            , r.profile_used
            , r.lookup_mode
            , r.source
            , r.insertion_timestamp
            , r.updated_timestamp
        FROM {table} AS r
        INNER JOIN wanted AS w
                ON w.origin_key = r.origin_key
               AND w.destiny_key = r.destiny_key
               AND w.profile_requested = r.profile_requested
        """,
        flat_params,
    ).fetchall()
    return {
        (str(row[0]), str(row[2]), str(row[12] or DEFAULT_PROFILE)): _row_to_dict(row)
        for row in rows
    }


def list_runs_by_coord_keys(
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[float, float, float, float, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    prepared: list[tuple[str, str, str]] = []
    for origin_lat, origin_lon, destiny_lat, destiny_lon, profile_requested in keys:
        coord_key = build_coord_lookup_key(origin_lat, origin_lon, destiny_lat, destiny_lon, profile_requested)
        if coord_key is not None:
            prepared.append(coord_key)
    if not prepared:
        return {}

    placeholders = ", ".join(["(?, ?, ?)"] * len(prepared))
    flat_params: list[Any] = []
    for row in prepared:
        flat_params.extend(row)

    rows = conn.execute(
        f"""
        WITH wanted(profile_requested, origin_coord_key, destiny_coord_key) AS (
            VALUES {placeholders}
        )
        SELECT
              r.origin_key
            , r.origin_name
            , r.destiny_key
            , r.destiny_name
            , r.distance_km
            , r.is_hgv
            , r.origin_lat
            , r.origin_lon
            , r.destiny_lat
            , r.destiny_lon
            , r.origin_coord_key
            , r.destiny_coord_key
            , r.profile_requested
            , r.profile_used
            , r.lookup_mode
            , r.source
            , r.insertion_timestamp
            , r.updated_timestamp
        FROM {table} AS r
        INNER JOIN wanted AS w
                ON w.profile_requested = r.profile_requested
               AND w.origin_coord_key = r.origin_coord_key
               AND w.destiny_coord_key = r.destiny_coord_key
        """,
        flat_params,
    ).fetchall()
    return {
        (
            str(row[12] or DEFAULT_PROFILE),
            str(row[10] or ""),
            str(row[11] or ""),
        ): _row_to_dict(row)
        for row in rows
    }


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
        , origin_coord_key
        , destiny_coord_key
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


def list_origin_names(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_TABLE,
    limit: int = 10_000,
) -> List[str]:
    """Return distinct cached origin labels only."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)

    sql = f"""
    SELECT origin_name
    FROM (
        SELECT DISTINCT TRIM(origin_name) AS origin_name
        FROM {table}
        WHERE TRIM(COALESCE(origin_name, '')) <> ''
    ) AS distinct_origins
    ORDER BY LOWER(origin_name) ASC, origin_name ASC
    LIMIT ?
    """
    rows = conn.execute(sql, (int(limit),)).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


def find_place_point(
    conn: DBConnection,
    *,
    place: str,
    table_name: str = DEFAULT_TABLE,
) -> Optional[Dict[str, Any]]:
    """Look up the latest cached coordinates for a place label in the routes table."""
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    place_key = _build_place_key(place)
    if not place_key:
        return None

    row = conn.execute(
        f"""
        SELECT
              label
            , lat
            , lon
            , role
            , updated_timestamp
            , insertion_timestamp
        FROM (
            SELECT
                  origin_name AS label
                , origin_lat AS lat
                , origin_lon AS lon
                , 'origin' AS role
                , updated_timestamp
                , insertion_timestamp
            FROM {table}
            WHERE origin_key = ?
              AND origin_lat IS NOT NULL
              AND origin_lon IS NOT NULL
            UNION ALL
            SELECT
                  destiny_name AS label
                , destiny_lat AS lat
                , destiny_lon AS lon
                , 'destiny' AS role
                , updated_timestamp
                , insertion_timestamp
            FROM {table}
            WHERE destiny_key = ?
              AND destiny_lat IS NOT NULL
              AND destiny_lon IS NOT NULL
        ) AS points
        ORDER BY CASE WHEN updated_timestamp IS NULL THEN 1 ELSE 0 END ASC
               , updated_timestamp DESC
               , CASE WHEN insertion_timestamp IS NULL THEN 1 ELSE 0 END ASC
               , insertion_timestamp DESC
               , label ASC
        LIMIT 1
        """,
        (place_key, place_key),
    ).fetchone()
    if not row:
        return None

    return {
        "label": str(row[0]),
        "lat": to_float(row[1]),
        "lon": to_float(row[2]),
        "role": str(row[3]),
        "updated_timestamp": row[4],
        "insertion_timestamp": row[5],
    }


def list_place_points(
    conn: DBConnection,
    *,
    places: Iterable[str],
    table_name: str = DEFAULT_TABLE,
) -> Dict[str, Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_main_table(conn, table)
    keys: list[str] = []
    for place in places:
        place_key = _build_place_key(place)
        if place_key:
            keys.append(place_key)
    if not keys:
        return {}

    placeholders = ", ".join(["(?)"] * len(keys))
    rows = conn.execute(
        f"""
        WITH wanted(place_key) AS (
            VALUES {placeholders}
        ),
        points AS (
            SELECT
                  origin_key AS place_key
                , origin_name AS label
                , origin_lat AS lat
                , origin_lon AS lon
                , 'origin' AS role
                , updated_timestamp
                , insertion_timestamp
            FROM {table}
            WHERE origin_lat IS NOT NULL
              AND origin_lon IS NOT NULL
            UNION ALL
            SELECT
                  destiny_key AS place_key
                , destiny_name AS label
                , destiny_lat AS lat
                , destiny_lon AS lon
                , 'destiny' AS role
                , updated_timestamp
                , insertion_timestamp
            FROM {table}
            WHERE destiny_lat IS NOT NULL
              AND destiny_lon IS NOT NULL
        )
        SELECT
              p.place_key
            , p.label
            , p.lat
            , p.lon
            , p.role
            , p.updated_timestamp
            , p.insertion_timestamp
        FROM points AS p
        INNER JOIN wanted AS w
                ON w.place_key = p.place_key
        ORDER BY p.place_key ASC
               , CASE WHEN p.updated_timestamp IS NULL THEN 1 ELSE 0 END ASC
               , p.updated_timestamp DESC
               , CASE WHEN p.insertion_timestamp IS NULL THEN 1 ELSE 0 END ASC
               , p.insertion_timestamp DESC
               , p.label ASC
        """,
        keys,
    ).fetchall()

    results: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        place_key = str(row[0])
        if place_key in results:
            continue
        results[place_key] = {
            "label": str(row[1]),
            "lat": to_float(row[2]),
            "lon": to_float(row[3]),
            "role": str(row[4]),
            "updated_timestamp": row[5],
            "insertion_timestamp": row[6],
        }
    return results

