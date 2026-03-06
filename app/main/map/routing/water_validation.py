from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path, haversine_km, point_to_segment_distance_km
from app.main.map.routing.marine_manual_overrides import apply_manual_route_overrides
from app.main.map.routing.marine_waypoints import (
    NAMED_MARINE_POINTS,
    point_names_to_latlon,
    resolve_port_approach_point_names,
)
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXED_WAYPOINTS_PATH = _REPO_ROOT / "data" / "raw" / "plot" / "fixed_waypoints.txt"
_CORNER_LAT = -5.2


def _coastal_score(lat: float, lon: float) -> float:
    if lat < _CORNER_LAT:
        return lat + 40.0
    return 40.0 + abs(lon)


def _parse_waypoint_line(line: str) -> tuple[float, float] | None:
    parts = [part for part in re.split(r"[\s,]+", str(line or "").strip()) if part]
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


@lru_cache(maxsize=1)
def load_reference_water_lane() -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    if _FIXED_WAYPOINTS_PATH.exists():
        try:
            for raw_line in _FIXED_WAYPOINTS_PATH.read_text(encoding="utf-8").splitlines():
                point = _parse_waypoint_line(raw_line)
                if point is not None:
                    points.append(point)
        except OSError as exc:
            _log.warning("Failed to read fixed maritime waypoints from '%s': %s", _FIXED_WAYPOINTS_PATH, exc)
    else:
        _log.warning("Fixed maritime waypoints file not found at '%s'.", _FIXED_WAYPOINTS_PATH)

    points.extend(NAMED_MARINE_POINTS.values())
    points.sort(key=lambda point: (_coastal_score(point[0], point[1]), point[0], point[1]))
    return dedupe_latlon_path(points)


def select_reference_water_lane_slice(
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    *,
    lane: Sequence[tuple[float, float]] | None = None,
) -> list[tuple[float, float]]:
    points = list(lane or load_reference_water_lane())
    if not points:
        return []

    origin_idx = _nearest_index(origin_latlon, points)
    dest_idx = _nearest_index(dest_latlon, points)

    if origin_idx <= dest_idx:
        return points[origin_idx : dest_idx + 1]
    return list(reversed(points[dest_idx : origin_idx + 1]))


def build_leg_reference_path(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
) -> list[tuple[float, float]]:
    origin_approach = point_names_to_latlon(resolve_port_approach_point_names(origin_port_name))
    dest_approach = point_names_to_latlon(resolve_port_approach_point_names(dest_port_name))

    origin_anchor = origin_approach[-1] if origin_approach else origin_latlon
    dest_anchor = dest_approach[-1] if dest_approach else dest_latlon

    water_lane = select_reference_water_lane_slice(origin_anchor, dest_anchor)
    water_lane = apply_manual_route_overrides(
        water_lane,
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
    )

    return dedupe_latlon_path(
        [origin_latlon]
        + origin_approach
        + water_lane
        + list(reversed(dest_approach))
        + [dest_latlon]
    )


def distance_to_water_km(
    point_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
) -> float:
    path = dedupe_latlon_path(reference_path)
    if not path:
        return float("inf")
    if len(path) == 1:
        return haversine_km(point_latlon[0], point_latlon[1], path[0][0], path[0][1])

    best_distance = float("inf")
    for idx in range(1, len(path)):
        distance = point_to_segment_distance_km(point_latlon, path[idx - 1], path[idx])
        if distance < best_distance:
            best_distance = distance
    return best_distance


def is_water_point(
    point_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    *,
    tolerance_km: float = 8.0,
) -> bool:
    return distance_to_water_km(point_latlon, reference_path) <= float(tolerance_km)


def _nearest_index(target_latlon: tuple[float, float], points: Sequence[tuple[float, float]]) -> int:
    target_lat, target_lon = target_latlon
    best_idx = 0
    best_distance = float("inf")

    for idx, (lat, lon) in enumerate(points):
        distance = haversine_km(target_lat, target_lon, lat, lon)
        if distance < best_distance:
            best_distance = distance
            best_idx = idx
    return best_idx
