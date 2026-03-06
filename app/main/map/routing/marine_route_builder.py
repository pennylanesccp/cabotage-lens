from __future__ import annotations

from app.main.map.routing.geometry_utils import dedupe_latlon_path, smooth_lonlat_path
from app.main.map.routing.marine_interpolation import interpolate_path_latlon
from app.main.map.routing.marine_manual_overrides import apply_manual_route_overrides
from app.main.map.routing.marine_point_correction import correct_path_to_water
from app.main.map.routing.marine_waypoints import point_names_to_latlon, resolve_port_approach_point_names
from app.main.map.routing.water_validation import select_reference_water_lane_slice


def build_marine_route_polyline(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    n_points: int = 100,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[list[float]]:
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

    seed_path = dedupe_latlon_path(
        [origin_latlon]
        + origin_approach
        + water_lane
        + list(reversed(dest_approach))
        + [dest_latlon]
    )
    if len(seed_path) < 2:
        return [[float(origin_latlon[1]), float(origin_latlon[0])], [float(dest_latlon[1]), float(dest_latlon[0])]]

    points_per_segment = max(int(n_points), 100)
    dense_path = interpolate_path_latlon(seed_path, n_points_per_segment=points_per_segment)

    validation_path = seed_path

    path_latlon = dense_path
    if str(style) == "Arc (pretty)":
        lonlat_path = [[float(lon), float(lat)] for lat, lon in path_latlon]
        smooth = max(int(smooth_window), 3) + max(0, int(round(float(curvature) * 8.0)))
        lonlat_path = smooth_lonlat_path(lonlat_path, smooth_window=smooth)
        path_latlon = [(float(point[1]), float(point[0])) for point in lonlat_path]

    corrected = correct_path_to_water(
        path_latlon,
        reference_path=validation_path,
        tolerance_km=8.0,
        step_km=1.0,
        max_search_km=20.0,
    )
    corrected[0] = origin_latlon
    corrected[-1] = dest_latlon
    return [[float(lon), float(lat)] for lat, lon in corrected]
