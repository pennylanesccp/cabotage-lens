# -*- coding: utf-8 -*-

"""
Durable place-point cache.

Stores canonicalized geographic points independently from routed legs so bulk
and heatmap flows can reuse geocoding across reruns without waiting for a
successful route cache write.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.db.core import (
    DBConnection,
    current_timestamp_sql,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
    to_float,
)

DEFAULT_TABLE = "place_points"

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      place_key            TEXT      PRIMARY KEY
    , label                TEXT      NOT NULL
    , lat                  REAL      NOT NULL
    , lon                  REAL      NOT NULL
    , uf                   TEXT
    , provider             TEXT
    , source               TEXT      NOT NULL DEFAULT 'geocode'
    , insertion_timestamp  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_updated_timestamp ON {table} (updated_timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_label ON {table} (label);",
)


def _normalize_place_key(value: Any) -> str:
    return ascii_place_key(value)


def _normalize_label(value: Any) -> str:
    return ascii_place_text(value)


def ensure_table(conn: DBConnection, table_name: str = DEFAULT_TABLE) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "place_points", table):
        return
    conn.execute(_DDL_SQL.format(table=table))
    for sql in _INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "place_points", table)


def _row_to_point(row: Iterable[Any]) -> Dict[str, Any]:
    values = list(row)
    return {
        "place_key": str(values[0]),
        "label": str(values[1]),
        "lat": to_float(values[2]),
        "lon": to_float(values[3]),
        "uf": (None if values[4] in (None, "") else str(values[4])),
        "provider": (None if values[5] in (None, "") else str(values[5])),
        "source": (None if values[6] in (None, "") else str(values[6])),
        "insertion_timestamp": values[7],
        "updated_timestamp": values[8],
    }


def find_point(
    conn: DBConnection,
    *,
    place: Any,
    table_name: str = DEFAULT_TABLE,
) -> Optional[Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_table(conn, table)
    place_key = _normalize_place_key(place)
    if not place_key:
        return None
    row = conn.execute(
        f"""
        SELECT
              place_key
            , label
            , lat
            , lon
            , uf
            , provider
            , source
            , insertion_timestamp
            , updated_timestamp
        FROM {table}
        WHERE place_key = ?
        LIMIT 1
        """,
        (place_key,),
    ).fetchone()
    if not row:
        return None
    return _row_to_point(row)


def list_points(
    conn: DBConnection,
    *,
    places: Iterable[Any],
    table_name: str = DEFAULT_TABLE,
) -> Dict[str, Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_table(conn, table)
    normalized = [_normalize_place_key(place) for place in places]
    keys = [key for key in normalized if key]
    if not keys:
        return {}

    placeholders = ", ".join(["(?)"] * len(keys))
    flat_params = list(keys)
    rows = conn.execute(
        f"""
        WITH wanted(place_key) AS (
            VALUES {placeholders}
        )
        SELECT
              p.place_key
            , p.label
            , p.lat
            , p.lon
            , p.uf
            , p.provider
            , p.source
            , p.insertion_timestamp
            , p.updated_timestamp
        FROM {table} AS p
        INNER JOIN wanted AS w
                ON w.place_key = p.place_key
        """,
        flat_params,
    ).fetchall()
    return {str(row[0]): _row_to_point(row) for row in rows}


def upsert_point(
    conn: DBConnection,
    *,
    place: Any,
    label: Any,
    lat: float,
    lon: float,
    uf: Optional[str] = None,
    provider: Optional[str] = None,
    source: str = "geocode",
    table_name: str = DEFAULT_TABLE,
) -> None:
    upsert_points(
        conn,
        rows=[
            {
                "place": place,
                "label": label,
                "lat": lat,
                "lon": lon,
                "uf": uf,
                "provider": provider,
                "source": source,
            }
        ],
        table_name=table_name,
    )


def upsert_points(
    conn: DBConnection,
    *,
    rows: Iterable[Dict[str, Any]],
    table_name: str = DEFAULT_TABLE,
) -> int:
    table = safe_table_name(table_name)
    ensure_table(conn, table)

    prepared: list[tuple[Any, ...]] = []
    for row in rows:
        place_key = _normalize_place_key(row.get("place"))
        label = _normalize_label(row.get("label") or row.get("place"))
        lat = to_float(row.get("lat"))
        lon = to_float(row.get("lon"))
        if not place_key or not label or lat is None or lon is None:
            continue
        prepared.append(
            (
                place_key,
                label,
                lat,
                lon,
                row.get("uf"),
                row.get("provider"),
                str(row.get("source") or "geocode").strip().lower() or "geocode",
            )
        )

    if not prepared:
        return 0

    conn.executemany(
        f"""
        INSERT INTO {table} (
              place_key
            , label
            , lat
            , lon
            , uf
            , provider
            , source
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(place_key) DO UPDATE SET
              label = excluded.label
            , lat = excluded.lat
            , lon = excluded.lon
            , uf = excluded.uf
            , provider = excluded.provider
            , source = excluded.source
            , updated_timestamp = {current_timestamp_sql()}
        """,
        prepared,
    )
    return len(prepared)
