from __future__ import annotations

from app.main.map.routing.marine_leg_interpolation import interpolate_leg_intermediate_points
from app.main.map.routing.marine_master_route import resolve_master_route_slice
from app.main.map.routing.marine_point_correction import correct_leg_intermediate_points
from app.main.map.routing.water_validation import build_leg_reference_path


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
    _ = (n_points, smooth_window, style, curvature)

    route_ports = resolve_master_route_slice(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
    )

    if len(route_ports) < 2:
        return [[float(origin_latlon[1]), float(origin_latlon[0])], [float(dest_latlon[1]), float(dest_latlon[0])]]

    path_latlon: list[tuple[float, float]] = [route_ports[0].latlon]
    intermediate_points_per_leg = 100

    for idx in range(1, len(route_ports)):
        leg_start = route_ports[idx - 1]
        leg_end = route_ports[idx]

        raw_leg_points = interpolate_leg_intermediate_points(
            leg_start.latlon,
            leg_end.latlon,
            n_points=intermediate_points_per_leg,
        )
        reference_path = build_leg_reference_path(
            origin_port_name=leg_start.name,
            dest_port_name=leg_end.name,
            origin_latlon=leg_start.latlon,
            dest_latlon=leg_end.latlon,
        )
        corrected_leg_points = correct_leg_intermediate_points(
            raw_leg_points,
            leg_start_latlon=leg_start.latlon,
            leg_end_latlon=leg_end.latlon,
            reference_path=reference_path,
            tolerance_km=8.0,
            step_km=1.0,
            max_search_km=20.0,
        )

        path_latlon.extend(corrected_leg_points)
        path_latlon.append(leg_end.latlon)

    return [[float(lon), float(lat)] for lat, lon in path_latlon]
