# -*- coding: utf-8 -*-

"""
Compatibility wrapper for the normalized location cache.

`place_points` used to store labels and coordinates inline. The active runtime
now persists canonical coordinates in `locations` and text aliases in
`location_aliases`. This module keeps the old helper names while delegating to
the new normalized storage.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from modules.infra.db.locations import (
    DEFAULT_ALIASES_TABLE as DEFAULT_TABLE,
    DEFAULT_LOCATIONS_TABLE,
    ensure_aliases_table as ensure_table,
    find_point,
    list_points,
    upsert_alias_point as upsert_point,
    upsert_alias_points as upsert_points,
)

__all__ = [
    "DEFAULT_TABLE",
    "DEFAULT_LOCATIONS_TABLE",
    "ensure_table",
    "find_point",
    "list_points",
    "upsert_point",
    "upsert_points",
]


def find_point_by_alias(
    conn,
    *,
    place: Any,
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Optional[Dict[str, Any]]:
    return find_point(
        conn,
        place=place,
        table_name=table_name,
        locations_table=locations_table,
    )


def list_points_by_aliases(
    conn,
    *,
    places: Iterable[Any],
    table_name: str = DEFAULT_TABLE,
    locations_table: str = DEFAULT_LOCATIONS_TABLE,
) -> Dict[str, Dict[str, Any]]:
    return list_points(
        conn,
        places=places,
        table_name=table_name,
        locations_table=locations_table,
    )
