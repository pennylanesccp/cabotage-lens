# -*- coding: utf-8 -*-

"""
Normalized road-route cache.

The active cache stores only canonical location references plus the durable
route attributes needed at runtime. Human-readable labels and coordinates live
in `locations` / `location_aliases`.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from modules.infra.db.core import (
    DBConnection,
    current_timestamp_sql,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
)
from modules.infra.db.locations import (
    DEFAULT_ALIASES_TABLE,
    DEFAULT_LOCATIONS_TABLE,
    coord_lookup_key,
    ensure_tables as ensure_location_tables,
    find_point,
    get_location_by_coords,
    get_or_create_location,
    list_locations_by_coords,
    list_points,
    normalize_place_key,
    upsert_alias_point,
)

DEFAULT_TABLE = "route_cache_entries"
DEFAULT_PROFILE = "driving-hgv"

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      id                  BIGSERIAL PRIMARY KEY
    , origin_location_id  BIGINT    NOT NULL REFERENCES {locations_table}(id) ON DELETE CASCADE
    , destiny_location_id BIGINT    NOT NULL REFERENCES {locations_table}(id) ON DELETE CASCADE
    , is_hgv              BOOLEAN   NOT NULL DEFAULT TRUE
    , fallback_profile    TEXT
    , provider            TEXT      NOT NULL DEFAULT 'ors'
    , distance_km         DOUBLE PRECISION
    , duration_s          DOUBLE PRECISION
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_origin_destiny_mode ON {table} (origin_location_id, destiny_location_id, is_hgv);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_updated_timestamp ON {table} (updated_timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_origin_location ON {table} (origin_location_id);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_destiny_location ON {table} (destiny_location_id);",
)


def normalize_profile(profile: Optional[str]) -> str:
    text = str(profile or DEFAULT_PROFILE).strip().lower()
    return text or DEFAULT_PROFILE


def profile_is_hgv(profile: Optional[str]) -> bool:
    return normalize_profile(profile) == "driving-hgv"


def build_label_lookup_key(origin: str, destiny: str, profile_requested: Optional[str]) -> tuple[str, str, str]:
    return (
        normalize_place_key(origin),
        normalize_place_key(destiny),
        normalize_profile(profile_requested),
    )


def build_coord_lookup_key(
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    destiny_lat: Optional[float],
    destiny_lon: Optional[float],
    profile_requested: Optional[str],
) -> Optional[tuple[str, str, str]]:
    origin_key = coord_lookup_key(origin_lat, origin_lon)
    destiny_key = coord_lookup_key(destiny_lat, destiny_lon)
    if origin_key is None or destiny_key is None:
        return None
    return (
        normalize_profile(profile_requested),
        f"{origin_key[0]},{origin_key[1]}",
        f"{destiny_key[0]},{destiny_key[1]}",
    )


def _requested_is_hgv(profile_requested: Optional[str], explicit_is_hgv: Optional[bool]) -> bool:
    if explicit_is_hgv is not None:
        return bool(explicit_is_hgv)
    return profile_is_hgv(profile_requested)


def ensure_main_table(
    conn: DBConnection,
    table_name: str = DEFAULT_TABLE,
    *,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    if schema_is_ready(conn, "route_cache_entries", table):
        return
    ensure_location_tables(conn, locations_table=locations, aliases_table=DEFAULT_ALIASES_TABLE)
    conn.execute(_DDL_SQL.format(table=table, locations_table=locations))
    for sql in _INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "route_cache_entries", table)


def _row_to_dict(row: Sequence[Any]) -> Dict[str, Any]:
    requested_profile = "driving-hgv" if bool(row[9]) else "driving-car"
    used_profile = str(row[10]) if row[10] not in (None, "") else requested_profile
    origin_label = str(row[3] or f"{float(row[4]):.6f}, {float(row[5]):.6f}")
    destiny_label = str(row[6] or f"{float(row[7]):.6f}, {float(row[8]):.6f}")
    return {
        "id": int(row[0]),
        "origin_location_id": int(row[1]),
        "destiny_location_id": int(row[2]),
        "origin": origin_label,
        "origin_lat": float(row[4]),
        "origin_lon": float(row[5]),
        "destiny": destiny_label,
        "destiny_lat": float(row[7]),
        "destiny_lon": float(row[8]),
        "is_hgv": bool(row[9]),
        "profile_requested": requested_profile,
        "profile_used": used_profile,
        "fallback_profile": (None if row[10] in (None, "") else str(row[10])),
        "source": str(row[11]),
        "provider": str(row[11]),
        "distance_km": (None if row[12] is None else float(row[12])),
        "duration_s": (None if row[13] is None else float(row[13])),
        "insertion_timestamp": row[14],
        "updated_timestamp": row[15],
    }


def _joined_select_sql(table: str, locations_table: str) -> str:
    return f"""
    SELECT
          rc.id
        , rc.origin_location_id
        , rc.destiny_location_id
        , o.label AS origin_label
        , o.lat6 AS origin_lat
        , o.lon6 AS origin_lon
        , d.label AS destiny_label
        , d.lat6 AS destiny_lat
        , d.lon6 AS destiny_lon
        , rc.is_hgv
        , rc.fallback_profile
        , rc.provider
        , rc.distance_km
        , rc.duration_s
        , rc.insertion_timestamp
        , rc.updated_timestamp
    FROM {table} AS rc
    INNER JOIN {locations_table} AS o
            ON o.id = rc.origin_location_id
    INNER JOIN {locations_table} AS d
            ON d.id = rc.destiny_location_id
    """


def _get_route_by_location_ids(
    conn: DBConnection,
    *,
    origin_location_id: int,
    destiny_location_id: int,
    is_hgv: bool,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)
    row = conn.execute(
        _joined_select_sql(table, locations)
        + """
        WHERE rc.origin_location_id = ?
          AND rc.destiny_location_id = ?
          AND rc.is_hgv = ?
        LIMIT 1
        """,
        (int(origin_location_id), int(destiny_location_id), bool(is_hgv)),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def _resolve_location_id_for_write(
    conn: DBConnection,
    *,
    label: str,
    lat: Optional[float],
    lon: Optional[float],
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> int:
    if lat is not None and lon is not None:
        point = upsert_alias_point(
            conn,
            place=label,
            label=label,
            lat=lat,
            lon=lon,
            source="route_cache",
            aliases_table=aliases_table,
            locations_table=locations_table,
        )
        if point is not None:
            return int(point["location_id"])

    cached = find_point(
        conn,
        place=label,
        table_name=aliases_table,
        locations_table=locations_table,
    )
    if cached is not None:
        return int(cached["location_id"])

    raise RuntimeError(f"Route cache requires coordinates or an existing alias for {label!r}.")


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
    duration_s: Optional[float] = None,
    profile_requested: Optional[str] = None,
    profile_used: Optional[str] = None,
    lookup_mode: str = "coords",
    source: str = "ors",
    is_hgv: Optional[bool] = None,
    origin_location_id: Optional[int] = None,
    destiny_location_id: Optional[int] = None,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Any]:
    del lookup_mode  # compatibility shim; normalized cache no longer stores lookup mode
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)

    requested_profile = normalize_profile(profile_requested)
    requested_is_hgv = _requested_is_hgv(requested_profile, is_hgv)
    normalized_source = str(source or "ors").strip().lower() or "ors"
    used_profile = normalize_profile(profile_used) if profile_used else requested_profile
    fallback_profile = None if used_profile == requested_profile else used_profile

    origin_location_id = origin_location_id or _resolve_location_id_for_write(
        conn,
        label=origin,
        lat=origin_lat,
        lon=origin_lon,
        aliases_table=aliases_table,
        locations_table=locations_table,
    )
    destiny_location_id = destiny_location_id or _resolve_location_id_for_write(
        conn,
        label=destiny,
        lat=destiny_lat,
        lon=destiny_lon,
        aliases_table=aliases_table,
        locations_table=locations_table,
    )

    row = conn.execute(
        f"""
        INSERT INTO {table} (
              origin_location_id
            , destiny_location_id
            , is_hgv
            , fallback_profile
            , provider
            , distance_km
            , duration_s
            , insertion_timestamp
            , updated_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, {current_timestamp_sql()}), COALESCE(?, {current_timestamp_sql()}))
        ON CONFLICT(origin_location_id, destiny_location_id, is_hgv) DO UPDATE SET
              fallback_profile = excluded.fallback_profile
            , provider = excluded.provider
            , distance_km = excluded.distance_km
            , duration_s = excluded.duration_s
            , updated_timestamp = COALESCE(excluded.updated_timestamp, {current_timestamp_sql()})
        RETURNING id
        """,
        (
            int(origin_location_id),
            int(destiny_location_id),
            bool(requested_is_hgv),
            fallback_profile,
            normalized_source,
            distance_km,
            duration_s,
            insertion_timestamp,
            updated_timestamp,
        ),
    ).fetchone()
    assert row is not None
    return _get_route_by_location_ids(
        conn,
        origin_location_id=int(origin_location_id),
        destiny_location_id=int(destiny_location_id),
        is_hgv=bool(requested_is_hgv),
        table_name=table,
        locations_table=locations,
    ) or {"id": int(row[0])}


def upsert_runs(
    conn: DBConnection,
    *,
    rows: Iterable[Dict[str, Any]],
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    return_rows: bool = False,
) -> int | List[Dict[str, Any]]:
    persisted: list[Dict[str, Any]] = []
    for row in rows:
        origin = str(row.get("origin") or "").strip()
        destiny = str(row.get("destiny") or "").strip()
        if not origin or not destiny:
            continue
        persisted_row = upsert_run(
            conn,
            origin=origin,
            destiny=destiny,
            origin_lat=row.get("origin_lat"),
            origin_lon=row.get("origin_lon"),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            distance_km=row.get("distance_km"),
            duration_s=row.get("duration_s"),
            profile_requested=row.get("profile_requested"),
            profile_used=row.get("profile_used"),
            source=row.get("source") or "ors",
            is_hgv=row.get("is_hgv"),
            origin_location_id=row.get("origin_location_id"),
            destiny_location_id=row.get("destiny_location_id"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            table_name=table_name,
            aliases_table=aliases_table,
            locations_table=locations_table,
        )
        persisted.append(persisted_row)
    if return_rows:
        return persisted
    return len(persisted)


def get_run(
    conn: DBConnection,
    *,
    origin: str,
    destiny: str,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    origin_point = find_point(conn, place=origin, table_name=aliases_table, locations_table=locations_table)
    destiny_point = find_point(conn, place=destiny, table_name=aliases_table, locations_table=locations_table)
    if origin_point is None or destiny_point is None:
        return None
    return _get_route_by_location_ids(
        conn,
        origin_location_id=int(origin_point["location_id"]),
        destiny_location_id=int(destiny_point["location_id"]),
        is_hgv=profile_is_hgv(profile_requested),
        table_name=table_name,
        locations_table=locations_table,
    )


def get_run_by_coords(
    conn: DBConnection,
    *,
    origin_lat: float,
    origin_lon: float,
    destiny_lat: float,
    destiny_lon: float,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    tolerance_deg: float = 1e-5,
) -> Optional[Dict[str, Any]]:
    del tolerance_deg
    origin_location = get_location_by_coords(conn, lat=origin_lat, lon=origin_lon, table_name=locations_table)
    destiny_location = get_location_by_coords(conn, lat=destiny_lat, lon=destiny_lon, table_name=locations_table)
    if origin_location is None or destiny_location is None:
        return None
    return _get_route_by_location_ids(
        conn,
        origin_location_id=int(origin_location["location_id"]),
        destiny_location_id=int(destiny_location["location_id"]),
        is_hgv=profile_is_hgv(profile_requested),
        table_name=table_name,
        locations_table=locations_table,
    )


def _list_routes_by_location_pairs(
    conn: DBConnection,
    *,
    pairs: Iterable[tuple[int, int, bool]],
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[tuple[int, int, bool], Dict[str, Any]]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)

    normalized = [(int(o), int(d), bool(mode)) for o, d, mode in pairs]
    if not normalized:
        return {}

    placeholders = ", ".join(["(?, ?, ?)"] * len(normalized))
    params: list[Any] = []
    for origin_location_id, destiny_location_id, is_hgv in normalized:
        params.extend((origin_location_id, destiny_location_id, is_hgv))

    rows = conn.execute(
        f"""
        WITH wanted(origin_location_id, destiny_location_id, is_hgv) AS (
            VALUES {placeholders}
        )
        """
        + _joined_select_sql(table, locations)
        + """
        INNER JOIN wanted AS w
                ON w.origin_location_id = rc.origin_location_id
               AND w.destiny_location_id = rc.destiny_location_id
               AND w.is_hgv = rc.is_hgv
        """,
        params,
    ).fetchall()
    return {
        (int(row[1]), int(row[2]), bool(row[9])): _row_to_dict(row)
        for row in rows
    }


def list_runs_by_label_keys(
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[str, str, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    prepared = [build_label_lookup_key(origin, destiny, profile_requested) for origin, destiny, profile_requested in keys]
    if not prepared:
        return {}

    place_keys: list[str] = []
    for origin_key, destiny_key, _profile in prepared:
        place_keys.append(origin_key)
        place_keys.append(destiny_key)
    points = list_points(conn, places=place_keys, table_name=aliases_table, locations_table=locations_table)

    pairs: list[tuple[int, int, bool]] = []
    requested_keys: list[tuple[str, str, str]] = []
    for origin_key, destiny_key, profile_requested in prepared:
        origin_point = points.get(origin_key)
        destiny_point = points.get(destiny_key)
        if origin_point is None or destiny_point is None:
            continue
        requested_keys.append((origin_key, destiny_key, profile_requested))
        pairs.append(
            (
                int(origin_point["location_id"]),
                int(destiny_point["location_id"]),
                profile_is_hgv(profile_requested),
            )
        )

    rows_by_pair = _list_routes_by_location_pairs(
        conn,
        pairs=pairs,
        table_name=table_name,
        locations_table=locations_table,
    )
    results: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for request_key, pair in zip(requested_keys, pairs):
        row = rows_by_pair.get(pair)
        if row is not None:
            results[request_key] = row
    return results


def list_runs_by_coord_keys(
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[float, float, float, float, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    prepared = list(keys)
    if not prepared:
        return {}

    coords_to_fetch: list[tuple[Any, Any]] = []
    for origin_lat, origin_lon, destiny_lat, destiny_lon, _profile in prepared:
        coords_to_fetch.append((origin_lat, origin_lon))
        coords_to_fetch.append((destiny_lat, destiny_lon))
    locations_by_coord = list_locations_by_coords(conn, coords=coords_to_fetch, table_name=locations_table)

    pairs: list[tuple[int, int, bool]] = []
    request_keys: list[tuple[str, str, str]] = []
    for origin_lat, origin_lon, destiny_lat, destiny_lon, profile_requested in prepared:
        origin_coord_key = coord_lookup_key(origin_lat, origin_lon)
        destiny_coord_key = coord_lookup_key(destiny_lat, destiny_lon)
        if origin_coord_key is None or destiny_coord_key is None:
            continue
        origin_location = locations_by_coord.get(origin_coord_key)
        destiny_location = locations_by_coord.get(destiny_coord_key)
        if origin_location is None or destiny_location is None:
            continue
        request_key = (
            normalize_profile(profile_requested),
            f"{origin_coord_key[0]},{origin_coord_key[1]}",
            f"{destiny_coord_key[0]},{destiny_coord_key[1]}",
        )
        request_keys.append(request_key)
        pairs.append(
            (
                int(origin_location["location_id"]),
                int(destiny_location["location_id"]),
                profile_is_hgv(profile_requested),
            )
        )

    rows_by_pair = _list_routes_by_location_pairs(
        conn,
        pairs=pairs,
        table_name=table_name,
        locations_table=locations_table,
    )
    results: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for request_key, pair in zip(request_keys, pairs):
        row = rows_by_pair.get(pair)
        if row is not None:
            results[request_key] = row
    return results


def overwrite_keys(
    conn: DBConnection,
    *,
    keys: Iterable[Tuple[str, str, Optional[str]]],
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> int:
    table = safe_table_name(table_name)
    ensure_main_table(conn, table, locations_table=locations_table)
    deleted = 0
    for origin, destiny, profile_requested in keys:
        origin_point = find_point(conn, place=origin, table_name=aliases_table, locations_table=locations_table)
        destiny_point = find_point(conn, place=destiny, table_name=aliases_table, locations_table=locations_table)
        if origin_point is None or destiny_point is None:
            continue
        cursor = conn.execute(
            f"""
            DELETE FROM {table}
            WHERE origin_location_id = ?
              AND destiny_location_id = ?
              AND is_hgv = ?
            """,
            (
                int(origin_point["location_id"]),
                int(destiny_point["location_id"]),
                profile_is_hgv(profile_requested),
            ),
        )
        deleted += int(cursor.rowcount or 0)
    return deleted


def delete_key(
    conn: DBConnection,
    *,
    origin: str,
    destiny: str,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    destiny_lat: Optional[float] = None,
    destiny_lon: Optional[float] = None,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> int:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)

    if None not in (origin_lat, origin_lon, destiny_lat, destiny_lon):
        origin_location = get_location_by_coords(
            conn,
            lat=origin_lat,
            lon=origin_lon,
            table_name=locations,
        )
        destiny_location = get_location_by_coords(
            conn,
            lat=destiny_lat,
            lon=destiny_lon,
            table_name=locations,
        )
        if origin_location is not None and destiny_location is not None:
            cursor = conn.execute(
                f"""
                DELETE FROM {table}
                WHERE origin_location_id = ?
                  AND destiny_location_id = ?
                  AND is_hgv = ?
                """,
                (
                    int(origin_location["location_id"]),
                    int(destiny_location["location_id"]),
                    profile_is_hgv(profile_requested),
                ),
            )
            deleted = int(cursor.rowcount or 0)
            if deleted:
                return deleted
    return overwrite_keys(
        conn,
        keys=[(origin, destiny, profile_requested)],
        table_name=table_name,
        aliases_table=aliases_table,
        locations_table=locations_table,
    )


def list_runs(
    conn: DBConnection,
    *,
    origin: Optional[str] = None,
    destiny: Optional[str] = None,
    profile_requested: Optional[str] = None,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)

    clauses: list[str] = []
    params: list[Any] = []

    if origin:
        point = find_point(conn, place=origin, table_name=aliases_table, locations_table=locations)
        if point is None:
            return []
        clauses.append("rc.origin_location_id = ?")
        params.append(int(point["location_id"]))
    if destiny:
        point = find_point(conn, place=destiny, table_name=aliases_table, locations_table=locations)
        if point is None:
            return []
        clauses.append("rc.destiny_location_id = ?")
        params.append(int(point["location_id"]))
    if profile_requested is not None:
        clauses.append("rc.is_hgv = ?")
        params.append(profile_is_hgv(profile_requested))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        _joined_select_sql(table, locations)
        + f"""
        {where}
        ORDER BY rc.updated_timestamp DESC, rc.insertion_timestamp DESC
        LIMIT ?
        """,
        params + [int(limit)],
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_place_names(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    limit: int = 10_000,
) -> List[str]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)
    rows = conn.execute(
        f"""
        SELECT label
        FROM (
            SELECT DISTINCT COALESCE(NULLIF(TRIM(o.label), ''), CONCAT(o.lat6::text, ', ', o.lon6::text)) AS label
            FROM {table} AS rc
            INNER JOIN {locations} AS o
                    ON o.id = rc.origin_location_id
            UNION
            SELECT DISTINCT COALESCE(NULLIF(TRIM(d.label), ''), CONCAT(d.lat6::text, ', ', d.lon6::text)) AS label
            FROM {table} AS rc
            INNER JOIN {locations} AS d
                    ON d.id = rc.destiny_location_id
        ) AS labels
        WHERE label IS NOT NULL
          AND label <> ''
        ORDER BY LOWER(label) ASC, label ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


def list_origin_names(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    limit: int = 10_000,
) -> List[str]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_main_table(conn, table, locations_table=locations)
    rows = conn.execute(
        f"""
        SELECT DISTINCT COALESCE(NULLIF(TRIM(o.label), ''), CONCAT(o.lat6::text, ', ', o.lon6::text)) AS label
        FROM {table} AS rc
        INNER JOIN {locations} AS o
                ON o.id = rc.origin_location_id
        WHERE COALESCE(NULLIF(TRIM(o.label), ''), CONCAT(o.lat6::text, ', ', o.lon6::text)) <> ''
        ORDER BY LOWER(label) ASC, label ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


def find_place_point(
    conn: DBConnection,
    *,
    place: str,
    table_name: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    return find_point(conn, place=place, table_name=table_name, locations_table=locations_table)


def list_place_points(
    conn: DBConnection,
    *,
    places: Iterable[str],
    table_name: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Dict[str, Any]]:
    return list_points(conn, places=places, table_name=table_name, locations_table=locations_table)
