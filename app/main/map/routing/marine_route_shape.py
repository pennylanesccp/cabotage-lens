from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import (
    dedupe_latlon_path,
    densify_latlon_path,
    haversine_km,
    smooth_lonlat_path,
)
from app.main.map.routing.marine_waypoints import (
    FALLBACK_TRUNK_POINT_NAMES,
    NAMED_MARINE_POINTS,
    point_names_to_latlon,
    resolve_major_corridor_point_names,
    resolve_port_approach_point_names,
)


def _nearest_trunk_index(target_latlon: tuple[float, float], trunk_point_names: Sequence[str]) -> int:
    target_lat, target_lon = target_latlon
    best_index = 0
    best_distance = float("inf")

    for idx, point_name in enumerate(trunk_point_names):
        point = NAMED_MARINE_POINTS.get(point_name)
        if point is None:
            continue
        distance = haversine_km(target_lat, target_lon, point[0], point[1])
        if distance < best_distance:
            best_distance = distance
            best_index = idx
    return best_index


def _fallback_trunk_segment(
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    origin_anchor_name: str | None,
    dest_anchor_name: str | None,
) -> list[str]:
    trunk_names = list(FALLBACK_TRUNK_POINT_NAMES)
    if not trunk_names:
        return []

    if origin_anchor_name in trunk_names:
        origin_idx = trunk_names.index(origin_anchor_name)
    else:
        origin_idx = _nearest_trunk_index(origin_latlon, trunk_names)

    if dest_anchor_name in trunk_names:
        dest_idx = trunk_names.index(dest_anchor_name)
    else:
        dest_idx = _nearest_trunk_index(dest_latlon, trunk_names)

    if origin_idx <= dest_idx:
        return trunk_names[origin_idx : dest_idx + 1]
    return list(reversed(trunk_names[dest_idx : origin_idx + 1]))


def _build_waypoint_names(
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
) -> list[str]:
    origin_approach = list(resolve_port_approach_point_names(origin_port_name))
    dest_approach = list(resolve_port_approach_point_names(dest_port_name))
    pair_corridor = resolve_major_corridor_point_names(origin_port_name, dest_port_name)

    if pair_corridor:
        return origin_approach + pair_corridor + list(reversed(dest_approach))

    origin_anchor_name = origin_approach[-1] if origin_approach else None
    dest_anchor_name = dest_approach[-1] if dest_approach else None
    trunk_segment = _fallback_trunk_segment(origin_latlon, dest_latlon, origin_anchor_name, dest_anchor_name)
    return origin_approach + trunk_segment + list(reversed(dest_approach))


def build_marine_route_path(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    n_points: int = 200,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[list[float]]:
    waypoint_names = _build_waypoint_names(origin_port_name, dest_port_name, origin_latlon, dest_latlon)
    waypoint_latlon = point_names_to_latlon(waypoint_names)

    path_latlon = dedupe_latlon_path([origin_latlon] + waypoint_latlon + [dest_latlon])
    point_count = max(int(n_points), 48)
    smooth = max(int(smooth_window), 5)

    if str(style) == "Arc (pretty)":
        point_count = int(point_count * 1.25)
        smooth += max(2, int(round(float(curvature) * 8.0)))

    dense = densify_latlon_path(path_latlon, n_points=point_count)
    return smooth_lonlat_path(dense, smooth_window=smooth)
