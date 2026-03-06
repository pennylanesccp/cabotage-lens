from __future__ import annotations

from app.main.map.routing.marine_coastal_route import build_coastal_leg_points
from app.main.map.routing.marine_master_route import is_river_leg, resolve_master_route_slice
from app.main.map.routing.marine_river_route import build_river_leg_points


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
    route_ports = resolve_master_route_slice(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
    )

    if len(route_ports) < 2:
        return [[float(origin_latlon[1]), float(origin_latlon[0])], [float(dest_latlon[1]), float(dest_latlon[0])]]

    path_latlon: list[tuple[float, float]] = [route_ports[0].latlon]
    intermediate_points_per_leg = max(int(n_points), 100)

    for idx in range(1, len(route_ports)):
        leg_start = route_ports[idx - 1]
        leg_end = route_ports[idx]

        if is_river_leg(leg_start.key, leg_end.key):
            leg_points = build_river_leg_points(
                origin_port_name=leg_start.name,
                dest_port_name=leg_end.name,
                leg_start_latlon=leg_start.latlon,
                leg_end_latlon=leg_end.latlon,
                n_points=intermediate_points_per_leg,
                smooth_window=smooth_window,
                style=style,
                curvature=curvature,
            )
        else:
            leg_points = build_coastal_leg_points(
                origin_port_name=leg_start.name,
                dest_port_name=leg_end.name,
                leg_start_latlon=leg_start.latlon,
                leg_end_latlon=leg_end.latlon,
                n_points=intermediate_points_per_leg,
                smooth_window=smooth_window,
                style=style,
                curvature=curvature,
            )

        path_latlon.extend(leg_points)
        path_latlon.append(leg_end.latlon)

    return [[float(lon), float(lat)] for lat, lon in path_latlon]
