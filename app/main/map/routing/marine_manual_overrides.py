from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path, haversine_km
from app.main.map.routing.marine_waypoints import normalize_port_name

REFERENCE_OVERRIDE_POINTS: dict[tuple[str, str], tuple[tuple[float, float], ...]] = {
    (
        normalize_port_name("Porto de Santarem"),
        normalize_port_name("Porto de Manaus"),
    ): (
        (-2.8752643, -56.7036805),
        (-3.3140755, -58.3955750),
        (-3.4456821, -58.8789734),
    ),
}


def apply_manual_route_overrides(
    path_latlon: Sequence[tuple[float, float]],
    *,
    origin_port_name: str,
    dest_port_name: str,
) -> list[tuple[float, float]]:
    path = dedupe_latlon_path(path_latlon)
    override = resolve_manual_override_points(origin_port_name=origin_port_name, dest_port_name=dest_port_name)
    if not path or not override:
        return path

    start_idx = _nearest_index(override[0], path)
    end_idx = _nearest_index(override[-1], path)

    if start_idx <= end_idx:
        return dedupe_latlon_path(path[:start_idx] + override + path[end_idx + 1 :])
    return dedupe_latlon_path(path + override)


def resolve_manual_override_points(
    *,
    origin_port_name: str,
    dest_port_name: str,
) -> list[tuple[float, float]]:
    origin_key = normalize_port_name(origin_port_name)
    dest_key = normalize_port_name(dest_port_name)

    direct = REFERENCE_OVERRIDE_POINTS.get((origin_key, dest_key))
    if direct is not None:
        return list(direct)

    reverse = REFERENCE_OVERRIDE_POINTS.get((dest_key, origin_key))
    if reverse is not None:
        return list(reversed(reverse))

    return []


def _nearest_index(target_latlon: tuple[float, float], path_latlon: Sequence[tuple[float, float]]) -> int:
    best_idx = 0
    best_distance = float("inf")
    for idx, point in enumerate(path_latlon):
        distance = haversine_km(target_latlon[0], target_latlon[1], point[0], point[1])
        if distance < best_distance:
            best_distance = distance
            best_idx = idx
    return best_idx
