from __future__ import annotations

from typing import Any, Dict, List, Tuple


def to_lonlat(path_latlon: List[Tuple[float, float]]) -> List[List[float]]:
    return [[float(lon), float(lat)] for lat, lon in path_latlon]


def path_endpoint_error(path_lonlat: List[List[float]], origin: Tuple[float, float], destiny: Tuple[float, float]) -> float:
    if not path_lonlat:
        return float("inf")

    o_lon, o_lat = path_lonlat[0]
    d_lon, d_lat = path_lonlat[-1]
    return (
        abs(o_lat - origin[0])
        + abs(o_lon - origin[1])
        + abs(d_lat - destiny[0])
        + abs(d_lon - destiny[1])
    )


def extract_leg_path(leg: Dict[str, Any], origin: Tuple[float, float], destiny: Tuple[float, float]) -> List[List[float]]:
    if not isinstance(leg, dict):
        return to_lonlat([origin, destiny])

    candidates = [
        leg.get("geometry"),
        leg.get("path"),
        leg.get("polyline"),
        leg.get("coords"),
        leg.get("coordinates"),
    ]

    for raw in candidates:
        if not isinstance(raw, list) or len(raw) < 2:
            continue

        first = raw[0]
        if isinstance(first, dict) and "lat" in first and "lon" in first:
            try:
                return [[float(p["lon"]), float(p["lat"])] for p in raw]
            except (TypeError, ValueError, KeyError):
                continue

        if isinstance(first, (list, tuple)) and len(first) >= 2:
            try:
                as_lonlat = [[float(p[0]), float(p[1])] for p in raw]
                as_latlon = [[float(p[1]), float(p[0])] for p in raw]
            except (TypeError, ValueError):
                continue

            score_lonlat = path_endpoint_error(as_lonlat, origin, destiny)
            score_latlon = path_endpoint_error(as_latlon, origin, destiny)
            return as_lonlat if score_lonlat <= score_latlon else as_latlon

    return to_lonlat([origin, destiny])
