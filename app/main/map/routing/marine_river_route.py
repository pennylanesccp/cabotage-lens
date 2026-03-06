from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path, densify_latlon_path, haversine_km, smooth_lonlat_path
from app.main.map.routing.marine_manual_overrides import apply_manual_route_overrides
from app.main.map.routing.marine_waypoints import point_names_to_latlon, resolve_port_approach_point_names

RIVER_TRUNK_POINT_NAMES: tuple[str, ...] = (
    "amazon-mouth",
    "macapa-channel",
    "santana-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
    "manaus-channel",
)


def build_river_leg_points(
    *,
    origin_port_name: str,
    dest_port_name: str,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    n_points: int = 100,
    smooth_window: int = 9,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[tuple[float, float]]:
    anchor_path = build_river_leg_anchor_path(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        leg_start_latlon=leg_start_latlon,
        leg_end_latlon=leg_end_latlon,
    )
    if len(anchor_path) < 2:
        return []

    total_points = max(int(n_points), 1) + 2
    dense_lonlat = densify_latlon_path(anchor_path, n_points=total_points)

    window = max(int(smooth_window), 5)
    if window % 2 == 0:
        window += 1
    if str(style) == "Arc (pretty)":
        window += 2
    if float(curvature) >= 0.3:
        window += 2

    smooth_lonlat = smooth_lonlat_path(dense_lonlat, smooth_window=window)
    smooth_latlon = [(float(point[1]), float(point[0])) for point in smooth_lonlat]
    smooth_latlon[0] = (float(leg_start_latlon[0]), float(leg_start_latlon[1]))
    smooth_latlon[-1] = (float(leg_end_latlon[0]), float(leg_end_latlon[1]))
    return smooth_latlon[1:-1]


def build_river_leg_anchor_path(
    *,
    origin_port_name: str,
    dest_port_name: str,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
) -> list[tuple[float, float]]:
    origin_approach = point_names_to_latlon(resolve_port_approach_point_names(origin_port_name))
    dest_approach = point_names_to_latlon(resolve_port_approach_point_names(dest_port_name))

    origin_anchor = origin_approach[-1] if origin_approach else leg_start_latlon
    dest_anchor = dest_approach[-1] if dest_approach else leg_end_latlon

    river_slice = select_river_trunk_slice(origin_anchor, dest_anchor)
    river_slice = apply_manual_route_overrides(
        river_slice,
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
    )

    return dedupe_latlon_path(
        [leg_start_latlon]
        + origin_approach
        + river_slice
        + list(reversed(dest_approach))
        + [leg_end_latlon]
    )


def select_river_trunk_slice(
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    *,
    trunk: Sequence[tuple[float, float]] | None = None,
) -> list[tuple[float, float]]:
    points = list(trunk or point_names_to_latlon(RIVER_TRUNK_POINT_NAMES))
    if not points:
        return []

    origin_idx = _nearest_index(origin_latlon, points)
    dest_idx = _nearest_index(dest_latlon, points)
    if origin_idx <= dest_idx:
        return points[origin_idx : dest_idx + 1]
    return list(reversed(points[dest_idx : origin_idx + 1]))


def _nearest_index(
    target_latlon: tuple[float, float],
    points: Sequence[tuple[float, float]],
) -> int:
    best_idx = 0
    best_distance = float("inf")
    for idx, point in enumerate(points):
        distance = haversine_km(target_latlon[0], target_latlon[1], point[0], point[1])
        if distance < best_distance:
            best_distance = distance
            best_idx = idx
    return best_idx
