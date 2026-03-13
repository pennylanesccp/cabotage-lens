from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional, Sequence

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.db.core import (
    DBConnection,
    current_timestamp_sql,
    mark_schema_ready,
    safe_table_name,
    schema_is_ready,
)

DEFAULT_LOCATIONS_TABLE = "locations"
DEFAULT_ALIASES_TABLE = "location_aliases"
_COORD_QUANT = Decimal("0.000001")

_LOCATIONS_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      id                  BIGSERIAL PRIMARY KEY
    , lat6                NUMERIC(9, 6) NOT NULL
    , lon6                NUMERIC(9, 6) NOT NULL
    , label               TEXT
    , street              TEXT
    , house_number        TEXT
    , neighborhood        TEXT
    , city                TEXT
    , state               TEXT
    , postal_code         TEXT
    , provider            TEXT
    , provider_payload    JSONB
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT ck_{table}_lat6 CHECK (lat6 BETWEEN -90.000000 AND 90.000000)
    , CONSTRAINT ck_{table}_lon6 CHECK (lon6 BETWEEN -180.000000 AND 180.000000)
);
"""

_LOCATIONS_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_lat_lon ON {table} (lat6, lon6);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_updated_timestamp ON {table} (updated_timestamp DESC);",
)

_ALIASES_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      place_key            TEXT PRIMARY KEY
    , alias_label          TEXT      NOT NULL
    , location_id          BIGINT    NOT NULL REFERENCES {locations_table}(id) ON DELETE CASCADE
    , provider             TEXT
    , source               TEXT      NOT NULL DEFAULT 'geocode'
    , insertion_timestamp  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_ALIASES_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_{table}_location_id ON {table} (location_id);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_updated_timestamp ON {table} (updated_timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_{table}_alias_label ON {table} (alias_label);",
)


def normalize_coordinate(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value)).quantize(_COORD_QUANT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_coordinates(lat: Any, lon: Any) -> Optional[tuple[Decimal, Decimal]]:
    lat6 = normalize_coordinate(lat)
    lon6 = normalize_coordinate(lon)
    if lat6 is None or lon6 is None:
        return None
    return lat6, lon6


def coord_lookup_key(lat: Any, lon: Any) -> Optional[tuple[str, str]]:
    coords = normalize_coordinates(lat, lon)
    if coords is None:
        return None
    return (format(coords[0], "f"), format(coords[1], "f"))


def normalize_place_label(value: Any) -> str:
    return ascii_place_text(value)


def normalize_place_key(value: Any) -> str:
    return ascii_place_key(value)


def ensure_locations_table(conn: DBConnection, table_name: str = DEFAULT_LOCATIONS_TABLE) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "locations", table):
        return
    conn.execute(_LOCATIONS_DDL_SQL.format(table=table))
    for sql in _LOCATIONS_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "locations", table)


def ensure_aliases_table(
    conn: DBConnection,
    table_name: str = DEFAULT_ALIASES_TABLE,
    *,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> None:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    if schema_is_ready(conn, "location_aliases", table):
        return
    ensure_locations_table(conn, locations)
    conn.execute(_ALIASES_DDL_SQL.format(table=table, locations_table=locations))
    for sql in _ALIASES_INDEX_SQL:
        conn.execute(sql.format(table=table))
    mark_schema_ready(conn, "location_aliases", table)


def ensure_tables(
    conn: DBConnection,
    *,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
) -> None:
    ensure_locations_table(conn, locations_table)
    ensure_aliases_table(conn, aliases_table, locations_table=locations_table)


def _row_to_location(row: Sequence[Any]) -> Dict[str, Any]:
    return {
        "location_id": int(row[0]),
        "lat": float(row[1]),
        "lon": float(row[2]),
        "label": (None if row[3] in (None, "") else str(row[3])),
        "street": (None if row[4] in (None, "") else str(row[4])),
        "house_number": (None if row[5] in (None, "") else str(row[5])),
        "neighborhood": (None if row[6] in (None, "") else str(row[6])),
        "city": (None if row[7] in (None, "") else str(row[7])),
        "state": (None if row[8] in (None, "") else str(row[8])),
        "postal_code": (None if row[9] in (None, "") else str(row[9])),
        "provider": (None if row[10] in (None, "") else str(row[10])),
        "provider_payload": row[11],
        "insertion_timestamp": row[12],
        "updated_timestamp": row[13],
    }


def _row_to_alias_point(row: Sequence[Any]) -> Dict[str, Any]:
    return {
        "location_id": int(row[0]),
        "place_key": str(row[1]),
        "label": str(row[2]),
        "lat": float(row[3]),
        "lon": float(row[4]),
        "uf": (None if row[5] in (None, "") else str(row[5])),
        "provider": (None if row[6] in (None, "") else str(row[6])),
        "source": (None if row[7] in (None, "") else str(row[7])),
        "insertion_timestamp": row[8],
        "updated_timestamp": row[9],
        "role": "alias",
    }


def get_location_by_coords(
    conn: DBConnection,
    *,
    lat: Any,
    lon: Any,
    table_name: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_locations_table(conn, table)
    coords = normalize_coordinates(lat, lon)
    if coords is None:
        return None
    row = conn.execute(
        f"""
        SELECT
              id
            , lat6
            , lon6
            , label
            , street
            , house_number
            , neighborhood
            , city
            , state
            , postal_code
            , provider
            , provider_payload
            , insertion_timestamp
            , updated_timestamp
        FROM {table}
        WHERE lat6 = ?
          AND lon6 = ?
        LIMIT 1
        """,
        coords,
    ).fetchone()
    if not row:
        return None
    return _row_to_location(row)


def list_locations_by_coords(
    conn: DBConnection,
    *,
    coords: Iterable[tuple[Any, Any]],
    table_name: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[tuple[str, str], Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_locations_table(conn, table)

    normalized: list[tuple[Decimal, Decimal]] = []
    for lat, lon in coords:
        pair = normalize_coordinates(lat, lon)
        if pair is not None:
            normalized.append(pair)
    if not normalized:
        return {}

    placeholders = ", ".join(["(?, ?)"] * len(normalized))
    params: list[Any] = []
    for lat6, lon6 in normalized:
        params.extend((lat6, lon6))

    rows = conn.execute(
        f"""
        WITH wanted(lat6, lon6) AS (
            VALUES {placeholders}
        )
        SELECT
              l.id
            , l.lat6
            , l.lon6
            , l.label
            , l.street
            , l.house_number
            , l.neighborhood
            , l.city
            , l.state
            , l.postal_code
            , l.provider
            , l.provider_payload
            , l.insertion_timestamp
            , l.updated_timestamp
        FROM {table} AS l
        INNER JOIN wanted AS w
                ON w.lat6 = l.lat6
               AND w.lon6 = l.lon6
        """,
        params,
    ).fetchall()
    return {
        (format(row[1], "f"), format(row[2], "f")): _row_to_location(row)
        for row in rows
    }


def get_or_create_location(
    conn: DBConnection,
    *,
    lat: Any,
    lon: Any,
    label: Any = None,
    street: Any = None,
    house_number: Any = None,
    neighborhood: Any = None,
    city: Any = None,
    state: Any = None,
    postal_code: Any = None,
    provider: Any = None,
    provider_payload: Any = None,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Any]:
    table = safe_table_name(table_name)
    ensure_locations_table(conn, table)
    coords = normalize_coordinates(lat, lon)
    if coords is None:
        raise RuntimeError("Canonical locations require latitude and longitude.")

    row = conn.execute(
        f"""
        INSERT INTO {table} (
              lat6
            , lon6
            , label
            , street
            , house_number
            , neighborhood
            , city
            , state
            , postal_code
            , provider
            , provider_payload
            , insertion_timestamp
            , updated_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, {current_timestamp_sql()}), COALESCE(?, {current_timestamp_sql()}))
        ON CONFLICT(lat6, lon6) DO UPDATE SET
              label = COALESCE({table}.label, EXCLUDED.label)
            , street = COALESCE({table}.street, EXCLUDED.street)
            , house_number = COALESCE({table}.house_number, EXCLUDED.house_number)
            , neighborhood = COALESCE({table}.neighborhood, EXCLUDED.neighborhood)
            , city = COALESCE({table}.city, EXCLUDED.city)
            , state = COALESCE({table}.state, EXCLUDED.state)
            , postal_code = COALESCE({table}.postal_code, EXCLUDED.postal_code)
            , provider = COALESCE({table}.provider, EXCLUDED.provider)
            , provider_payload = COALESCE({table}.provider_payload, EXCLUDED.provider_payload)
            , updated_timestamp = COALESCE(EXCLUDED.updated_timestamp, {current_timestamp_sql()})
        RETURNING
              id
            , lat6
            , lon6
            , label
            , street
            , house_number
            , neighborhood
            , city
            , state
            , postal_code
            , provider
            , provider_payload
            , insertion_timestamp
            , updated_timestamp
        """,
        (
            coords[0],
            coords[1],
            normalize_place_label(label) or None,
            normalize_place_label(street) or None,
            normalize_place_label(house_number) or None,
            normalize_place_label(neighborhood) or None,
            normalize_place_label(city) or None,
            normalize_place_label(state) or None,
            normalize_place_label(postal_code) or None,
            normalize_place_label(provider) or None,
            provider_payload,
            insertion_timestamp,
            updated_timestamp,
        ),
    ).fetchone()
    assert row is not None
    return _row_to_location(row)


def upsert_alias(
    conn: DBConnection,
    *,
    place: Any,
    location_id: int,
    alias_label: Any,
    provider: Any = None,
    source: str = "geocode",
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    table = safe_table_name(table_name)
    ensure_aliases_table(conn, table, locations_table=locations_table)
    place_key = normalize_place_key(place)
    label = normalize_place_label(alias_label or place)
    if not place_key or not label:
        return None

    row = conn.execute(
        f"""
        INSERT INTO {table} (
              place_key
            , alias_label
            , location_id
            , provider
            , source
            , insertion_timestamp
            , updated_timestamp
        ) VALUES (?, ?, ?, ?, ?, COALESCE(?, {current_timestamp_sql()}), COALESCE(?, {current_timestamp_sql()}))
        ON CONFLICT(place_key) DO UPDATE SET
              alias_label = EXCLUDED.alias_label
            , location_id = EXCLUDED.location_id
            , provider = COALESCE(EXCLUDED.provider, {table}.provider)
            , source = COALESCE(EXCLUDED.source, {table}.source)
            , updated_timestamp = COALESCE(EXCLUDED.updated_timestamp, {current_timestamp_sql()})
        RETURNING place_key
        """,
        (
            place_key,
            label,
            int(location_id),
            normalize_place_label(provider) or None,
            str(source or "geocode").strip().lower() or "geocode",
            insertion_timestamp,
            updated_timestamp,
        ),
    ).fetchone()
    if not row:
        return None
    return find_point(
        conn,
        place=place_key,
        table_name=table_name,
        locations_table=locations_table,
    )


def upsert_alias_point(
    conn: DBConnection,
    *,
    place: Any,
    label: Any,
    lat: Any,
    lon: Any,
    uf: Any = None,
    provider: Any = None,
    source: str = "geocode",
    street: Any = None,
    house_number: Any = None,
    neighborhood: Any = None,
    city: Any = None,
    postal_code: Any = None,
    provider_payload: Any = None,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    ensure_tables(conn, locations_table=locations_table, aliases_table=aliases_table)
    location = get_or_create_location(
        conn,
        lat=lat,
        lon=lon,
        label=label,
        street=street,
        house_number=house_number,
        neighborhood=neighborhood,
        city=city,
        state=uf,
        postal_code=postal_code,
        provider=provider,
        provider_payload=provider_payload,
        insertion_timestamp=insertion_timestamp,
        updated_timestamp=updated_timestamp,
        table_name=locations_table,
    )

    aliases_to_write = [normalize_place_key(place)]
    label_key = normalize_place_key(label)
    if label_key and label_key not in aliases_to_write:
        aliases_to_write.append(label_key)

    point: Optional[Dict[str, Any]] = None
    for alias_key in aliases_to_write:
        point = upsert_alias(
            conn,
            place=alias_key,
            location_id=location["location_id"],
            alias_label=(label if alias_key == label_key and label_key else place),
            provider=provider,
            source=source,
            insertion_timestamp=insertion_timestamp,
            updated_timestamp=updated_timestamp,
            table_name=aliases_table,
            locations_table=locations_table,
        )
    return point


def upsert_alias_points(
    conn: DBConnection,
    *,
    rows: Iterable[Dict[str, Any]],
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Dict[str, Any]]:
    ensure_tables(conn, locations_table=locations_table, aliases_table=aliases_table)
    results: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        place_key = normalize_place_key(row.get("place"))
        point = upsert_alias_point(
            conn,
            place=row.get("place"),
            label=row.get("label") or row.get("place"),
            lat=row.get("lat"),
            lon=row.get("lon"),
            uf=row.get("uf") or row.get("state"),
            provider=row.get("provider"),
            source=str(row.get("source") or "geocode").strip().lower() or "geocode",
            street=row.get("street"),
            house_number=row.get("house_number"),
            neighborhood=row.get("neighborhood"),
            city=row.get("city"),
            postal_code=row.get("postal_code"),
            provider_payload=row.get("provider_payload"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            aliases_table=aliases_table,
            locations_table=locations_table,
        )
        if place_key and point is not None:
            results[place_key] = point
    return results


def find_point(
    conn: DBConnection,
    *,
    place: Any,
    table_name: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_aliases_table(conn, table, locations_table=locations)
    place_key = normalize_place_key(place)
    if not place_key:
        return None

    row = conn.execute(
        f"""
        SELECT
              l.id
            , a.place_key
            , COALESCE(NULLIF(l.label, ''), a.alias_label)
            , l.lat6
            , l.lon6
            , l.state
            , COALESCE(NULLIF(a.provider, ''), l.provider)
            , a.source
            , a.insertion_timestamp
            , a.updated_timestamp
        FROM {table} AS a
        INNER JOIN {locations} AS l
                ON l.id = a.location_id
        WHERE a.place_key = ?
        LIMIT 1
        """,
        (place_key,),
    ).fetchone()
    if not row:
        return None
    return _row_to_alias_point(row)


def list_points(
    conn: DBConnection,
    *,
    places: Iterable[Any],
    table_name: str = DEFAULT_ALIASES_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Dict[str, Any]]:
    table = safe_table_name(table_name)
    locations = safe_table_name(locations_table)
    ensure_aliases_table(conn, table, locations_table=locations)

    keys = [normalize_place_key(place) for place in places]
    keys = [key for key in keys if key]
    if not keys:
        return {}

    placeholders = ", ".join(["(?)"] * len(keys))
    rows = conn.execute(
        f"""
        WITH wanted(place_key) AS (
            VALUES {placeholders}
        )
        SELECT
              l.id
            , a.place_key
            , COALESCE(NULLIF(l.label, ''), a.alias_label)
            , l.lat6
            , l.lon6
            , l.state
            , COALESCE(NULLIF(a.provider, ''), l.provider)
            , a.source
            , a.insertion_timestamp
            , a.updated_timestamp
        FROM {table} AS a
        INNER JOIN {locations} AS l
                ON l.id = a.location_id
        INNER JOIN wanted AS w
                ON w.place_key = a.place_key
        """,
        keys,
    ).fetchall()
    return {str(row[1]): _row_to_alias_point(row) for row in rows}


def list_location_labels(
    conn: DBConnection,
    *,
    table_name: str = DEFAULT_LOCATIONS_TABLE,
    aliases_table: str = DEFAULT_ALIASES_TABLE,
    limit: int = 10_000,
) -> list[str]:
    table = safe_table_name(table_name)
    aliases = safe_table_name(aliases_table)
    ensure_tables(conn, locations_table=table, aliases_table=aliases)
    rows = conn.execute(
        f"""
        SELECT label
        FROM (
            SELECT
                COALESCE(
                    NULLIF(TRIM(l.label), ''),
                    MIN(NULLIF(TRIM(a.alias_label), ''))
                ) AS label
            FROM {table} AS l
            LEFT JOIN {aliases} AS a
                   ON a.location_id = l.id
            GROUP BY l.id, l.label
        ) AS labels
        WHERE label IS NOT NULL
          AND label <> ''
        ORDER BY LOWER(label) ASC, label ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]
